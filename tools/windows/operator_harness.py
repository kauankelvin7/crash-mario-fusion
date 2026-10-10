"""Fail-closed, opt-in keyboard operator for the two known Windows game windows."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import struct
import sys
import time

TARGETS = {
    "crash": "CrashBandicoot.exe",
    "mario": "sm64.us.f3dex2e.exe",
}
SAFE_VKS = frozenset((*range(0x30, 0x3A), *range(0x41, 0x5B), 0x08, 0x09, 0x0D, 0x1B, 0x20,
                      0x25, 0x26, 0x27, 0x28, 0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67,
                      0x68, 0x69, 0x6A, 0x6B, 0x6D, 0x6E, 0x6F))
MAX_SECONDS = 5.0
CHECK_INTERVAL = 0.025


class SafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowTarget:
    hwnd: int
    pid: int
    image_path: str


class Win32:
    def __init__(self):
        if os.name != "nt" or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise SafetyError("This operator requires 64-bit Windows.")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self._configure()

    def _configure(self):
        self.user32.EnumWindows.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetForegroundWindow.argtypes = []
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL
        self.user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
        self.user32.GetClientRect.restype = wintypes.BOOL
        self.user32.GetDC.argtypes = [wintypes.HWND]
        self.user32.GetDC.restype = wintypes.HDC
        self.user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        self.user32.ReleaseDC.restype = ctypes.c_int
        self.user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
        self.user32.PrintWindow.restype = wintypes.BOOL
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
        self.gdi32.CreateCompatibleDC.restype = wintypes.HDC
        self.gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
        self.gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
        self.gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        self.gdi32.SelectObject.restype = wintypes.HGDIOBJ
        self.gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        self.gdi32.DeleteObject.restype = wintypes.BOOL
        self.gdi32.DeleteDC.argtypes = [wintypes.HDC]
        self.gdi32.DeleteDC.restype = wintypes.BOOL
        self.gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
        self.gdi32.GetDIBits.restype = ctypes.c_int
        # HWND-scoped messages avoid a global SendInput foreground race.
        self.user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                             wintypes.WPARAM, wintypes.LPARAM]
        self.user32.PostMessageW.restype = wintypes.BOOL
        self.user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        self.user32.MapVirtualKeyW.restype = wintypes.UINT

    def process_image(self, pid):
        handle = self.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            raise SafetyError("Cannot verify target process identity.")
        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not self.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                raise SafetyError("Cannot read target process image path.")
            return buffer.value
        finally:
            self.kernel32.CloseHandle(handle)

    def find_target(self, game):
        expected = TARGETS[game].casefold()
        matches = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def visit(hwnd, _):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            pid = wintypes.DWORD()
            if not self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)) or not pid.value:
                return True
            try:
                path = self.process_image(pid.value)
            except SafetyError:
                return True
            if Path(path).name.casefold() == expected:
                matches.append(WindowTarget(int(hwnd), pid.value, path))
            return True

        if not self.user32.EnumWindows(callback_type(visit), 0):
            raise SafetyError("Windows could not enumerate top-level windows.")
        if len(matches) != 1:
            raise SafetyError(f"Expected exactly one visible {TARGETS[game]} window; found {len(matches)}.")
        return matches[0]

    def verify(self, game, target, require_focus=True):
        if not self.user32.IsWindow(target.hwnd):
            raise SafetyError("Target window no longer exists.")
        pid = wintypes.DWORD()
        if not self.user32.GetWindowThreadProcessId(target.hwnd, ctypes.byref(pid)) or pid.value != target.pid:
            raise SafetyError("Window process changed; refusing input.")
        path = self.process_image(pid.value)
        if path.casefold() != target.image_path.casefold() or Path(path).name.casefold() != TARGETS[game].casefold():
            raise SafetyError("Window executable changed; refusing input.")
        if require_focus and int(self.user32.GetForegroundWindow() or 0) != target.hwnd:
            raise SafetyError("Target lost foreground focus; refusing further input.")
        self._verified_hwnd = target.hwnd
        self._verified_pid = target.pid

    def focus_target(self, game, target):
        # Verify process identity before asking Windows to foreground it.
        self.verify(game, target, require_focus=False)
        self.user32.SetForegroundWindow(target.hwnd)
        time.sleep(0.12)
        self.verify(game, target)

    def key_event(self, vk, key_up=False):
        hwnd = getattr(self, "_verified_hwnd", None)
        expected_pid = getattr(self, "_verified_pid", None)
        if not hwnd or not expected_pid:
            raise SafetyError("Game HWND was not verified before input.")
        pid = wintypes.DWORD()
        if not self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)) or pid.value != expected_pid:
            raise SafetyError("Game HWND changed owner; input blocked.")
        scan = int(self.user32.MapVirtualKeyW(vk, 0))
        if not 0 < scan <= 0xFF:
            raise SafetyError("Unsupported scan code; input blocked.")
        extended = 0x01000000 if vk in (0x25, 0x26, 0x27, 0x28) else 0
        transition = 0xC0000000 if key_up else 0
        lparam = 1 | (scan << 16) | extended | transition
        msg = 0x0101 if key_up else 0x0100
        if not self.user32.PostMessageW(hwnd, msg, vk, lparam):
            raise SafetyError("Targeted game-window key message failed.")

    def capture_client_bmp(self, target, destination):
        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

        self.verify("crash" if Path(target.image_path).name == TARGETS["crash"] else "mario", target)
        rect = RECT()
        if not self.user32.GetClientRect(target.hwnd, ctypes.byref(rect)):
            raise SafetyError("Cannot determine game client area.")
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if width <= 0 or height <= 0 or width * height > 20_000_000:
            raise SafetyError("Client area dimensions are invalid or exceed the capture limit.")
        dc = self.user32.GetDC(target.hwnd)
        memory_dc = self.gdi32.CreateCompatibleDC(dc)
        bitmap = self.gdi32.CreateCompatibleBitmap(dc, width, height)
        old = self.gdi32.SelectObject(memory_dc, bitmap)
        try:
            if not self.user32.PrintWindow(target.hwnd, memory_dc, 1):
                raise SafetyError("Window-only client capture failed.")
            info = BITMAPINFO()
            info.bmiHeader = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32, 0, width * height * 4, 0, 0, 0, 0)
            pixels = ctypes.create_string_buffer(width * height * 4)
            rows = self.gdi32.GetDIBits(dc, bitmap, 0, height, pixels, ctypes.byref(info), 0)
            if rows != height:
                raise SafetyError("Could not read target-window pixels.")
            self.verify("crash" if Path(target.image_path).name == TARGETS["crash"] else "mario", target)
            destination.parent.mkdir(parents=True, exist_ok=True)
            row_size = width * 4
            image = b"".join(pixels.raw[y * row_size:(y + 1) * row_size] for y in range(height))
            with destination.open("xb") as output:
                output.write(b"BM" + struct.pack("<IHHI", 54 + len(image), 0, 0, 54))
                output.write(struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 32, 0, len(image), 2835, 2835, 0, 0))
                output.write(image)
            return destination
        finally:
            self.gdi32.SelectObject(memory_dc, old)
            self.gdi32.DeleteObject(bitmap)
            self.gdi32.DeleteDC(memory_dc)
            self.user32.ReleaseDC(target.hwnd, dc)


def run_action(api, game, target, vk, seconds, abort_check=lambda: False, sleep=time.sleep):
    if not 0 < seconds <= MAX_SECONDS:
        raise SafetyError("Action duration must be greater than 0 and at most 5 seconds.")
    api.verify(game, target)
    api.key_event(vk)
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            if abort_check():
                raise SafetyError("Aborted by operator.")
            api.verify(game, target)
            sleep(min(CHECK_INTERVAL, max(0.0, deadline - time.monotonic())))
    finally:
        api.key_event(vk, key_up=True)


def local_capture_dir():
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        raise SafetyError("LOCALAPPDATA is unavailable; private capture refused.")
    return Path(root) / "CrashMarioFusion" / "operator-captures"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bounded, local-only keyboard and client-window capture helper.")
    parser.add_argument("game", choices=TARGETS)
    parser.add_argument("--action", choices=("up", "down", "left", "right", "jump", "menu"))
    parser.add_argument("--vk", type=lambda value: int(value, 0), help="Explicit configured Windows virtual-key code, e.g. 0x20")
    parser.add_argument("--seconds", type=float, default=0.15)
    parser.add_argument("--execute", action="store_true", help="Required to send input; dry-run is the default")
    parser.add_argument("--capture-client", action="store_true", help="Save only this game's client image under LOCALAPPDATA")
    args = parser.parse_args(argv)
    try:
        if (args.action is None) != (args.vk is None):
            raise SafetyError("Supply both --action and --vk, or neither.")
        if args.action and not 0 < args.seconds <= MAX_SECONDS:
            raise SafetyError("Action duration must be greater than 0 and at most 5 seconds.")
        if args.vk is not None and args.vk not in SAFE_VKS:
            raise SafetyError("Virtual-key code is not in the allowlist of ordinary game keys.")
        if args.execute and args.action is None:
            raise SafetyError("--execute requires --action and --vk.")
        api = Win32()
        target = api.find_target(args.game)
        if args.execute or args.capture_client:
            api.focus_target(args.game, target)
        else:
            api.verify(args.game, target, require_focus=False)
        print(f"TARGET VERIFIED: {args.game} pid={target.pid} hwnd=0x{target.hwnd:x}")
        if args.action:
            if args.execute:
                import msvcrt
                run_action(api, args.game, target, args.vk, args.seconds, lambda: msvcrt.kbhit() and msvcrt.getwch() == "\x1b")
                print("INPUT SENT; gameplay outcome NOT_VERIFIED.")
            else:
                print(f"DRY RUN: {args.action} vk=0x{args.vk:02x} duration={args.seconds:g}s; no input sent.")
        elif args.execute:
            raise SafetyError("--execute requires --action and --vk.")
        if args.capture_client:
            name = f"{args.game}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.bmp"
            path = api.capture_client_bmp(target, local_capture_dir() / name)
            print(f"CLIENT-ONLY IMAGE saved locally: {path}")
        return 0
    except (SafetyError, OSError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    import msvcrt
    raise SystemExit(main())
