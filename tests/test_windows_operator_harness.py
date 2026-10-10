import unittest
import ctypes
from ctypes import wintypes

from tools.windows.operator_harness import MAX_SECONDS, SAFE_VKS, SafetyError, TARGETS, WindowTarget, Win32, run_action


class FakeWin32:
    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.verifications = 0
        self.events = []

    def verify(self, game, target):
        self.verifications += 1
        if self.fail_at == self.verifications:
            raise SafetyError("focus lost")

    def key_event(self, vk, key_up=False):
        self.events.append((vk, key_up))


class OperatorHarnessTests(unittest.TestCase):
    def setUp(self):
        self.target = WindowTarget(123, 456, r"C:\games\sm64.us.f3dex2e.exe")

    def test_targets_are_the_only_allowed_images(self):
        self.assertEqual(TARGETS, {"crash": "CrashBandicoot.exe", "mario": "sm64.us.f3dex2e.exe"})

    def test_key_allowlist_excludes_system_shortcuts(self):
        self.assertIn(0x20, SAFE_VKS)
        self.assertIn(0x5A, SAFE_VKS)
        self.assertNotIn(0x5B, SAFE_VKS)
        self.assertNotIn(0x73, SAFE_VKS)

    def test_rejects_zero_negative_and_over_five_second_actions(self):
        for seconds in (0, -0.1, MAX_SECONDS + 0.01):
            with self.subTest(seconds=seconds), self.assertRaises(SafetyError):
                run_action(FakeWin32(), "mario", self.target, 0x20, seconds)

    def test_held_action_is_released_after_success(self):
        api = FakeWin32()
        run_action(api, "mario", self.target, 0x20, 0.001, sleep=lambda _: None)
        self.assertEqual(api.events, [(0x20, False), (0x20, True)])

    def test_focus_loss_stops_action_and_releases_held_key(self):
        api = FakeWin32(fail_at=2)
        with self.assertRaisesRegex(SafetyError, "focus lost"):
            run_action(api, "mario", self.target, 0x20, 0.1, sleep=lambda _: None)
        self.assertEqual(api.events, [(0x20, False), (0x20, True)])

    def test_wrong_target_fails_before_key_down(self):
        api = FakeWin32(fail_at=1)
        with self.assertRaisesRegex(SafetyError, "focus lost"):
            run_action(api, "mario", self.target, 0x20, 0.1, sleep=lambda _: None)
        self.assertEqual(api.events, [])

    def test_operator_abort_releases_held_key(self):
        api = FakeWin32()
        with self.assertRaisesRegex(SafetyError, "Aborted"):
            run_action(api, "mario", self.target, 0x20, 0.1, abort_check=lambda: True)
        self.assertEqual(api.events, [(0x20, False), (0x20, True)])

    def test_native_messages_are_scoped_to_verified_game_hwnd(self):
        class FakeUser32:
            def __init__(self):
                self.events = []
                self.scan = 0x11

            def GetWindowThreadProcessId(self, hwnd, out_pid):
                ctypes.cast(out_pid, ctypes.POINTER(wintypes.DWORD)).contents.value = 456
                return 1

            def MapVirtualKeyW(self, key, conversion):
                return self.scan

            def PostMessageW(self, hwnd, msg, key, lparam):
                self.events.append((hwnd, msg, key, lparam))
                return True

        api = Win32.__new__(Win32)
        api.user32 = FakeUser32()
        api._verified_hwnd = 123
        api._verified_pid = 456
        api.key_event(0x57)
        api.key_event(0x57, key_up=True)
        self.assertEqual(api.user32.events,
                         [(123, 0x100, 0x57, 0x00110001),
                          (123, 0x101, 0x57, 0xC0110001)])
        api.user32.scan = 0x48
        api.key_event(0x26)
        self.assertEqual(api.user32.events[-1][3], 0x01480001)
        api._verified_pid = 999
        with self.assertRaises(SafetyError):
            api.key_event(0x57)
        self.assertEqual(len(api.user32.events), 3)


if __name__ == "__main__":
    unittest.main()
