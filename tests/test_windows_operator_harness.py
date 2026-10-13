import unittest
import ctypes
import io
from ctypes import wintypes
from unittest.mock import patch

from tools.windows.operator_harness import MAX_SECONDS, SAFE_VKS, SafetyError, TARGETS, WindowTarget, Win32, main, observe_client, run_action


class FakeWin32:
    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.verifications = 0
        self.events = []
        self.clock = lambda: 0
        self.focus_after = 0
        self.focus_lost_at = float("inf")

    def verify(self, game, target, require_focus=True):
        self.verifications += 1
        if self.fail_at == self.verifications:
            raise SafetyError("focus lost")
        if require_focus and not self.is_foreground(target):
            raise SafetyError("focus lost")

    def is_foreground(self, target):
        return self.focus_after <= self.clock() < self.focus_lost_at

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

    def observation(self, api, seconds, captures):
        class Clock:
            now = 0
            def __call__(self):
                return self.now
            def sleep(self, seconds):
                self.now += seconds
        clock = Clock()
        api.clock = clock
        return observe_client(api, "mario", self.target, seconds,
                              lambda: captures.append(clock()),
                              clock=clock, sleep=clock.sleep)

    def test_observation_waits_for_actual_focus_and_sends_no_keys(self):
        api = FakeWin32()
        api.focus_after = 0.3
        captures = []
        self.assertEqual(self.observation(api, 6, captures), 2)
        self.assertGreaterEqual(captures[0], 0.3)
        self.assertGreaterEqual(captures[1] - captures[0], 5)
        self.assertEqual(api.events, [])

    def test_observation_timeout_never_captures_unfocused_window(self):
        api = FakeWin32()
        api.focus_after = float("inf")
        captures = []
        with self.assertRaisesRegex(SafetyError, "expired"):
            self.observation(api, 1, captures)
        self.assertEqual(captures, [])
        self.assertEqual(api.events, [])

    def test_observation_rechecks_identity_while_waiting_for_focus(self):
        api = FakeWin32(fail_at=2)
        api.focus_after = 0.5
        captures = []
        with self.assertRaises(SafetyError):
            self.observation(api, 1, captures)
        self.assertEqual(captures, [])

    def test_observation_stops_on_focus_loss_after_first_capture(self):
        api = FakeWin32()
        api.focus_lost_at = 0.2
        captures = []
        with self.assertRaisesRegex(SafetyError, "focus lost"):
            self.observation(api, 10, captures)
        self.assertEqual(captures, [0])
        self.assertEqual(api.events, [])

    def test_observation_rejects_invalid_or_unbounded_duration(self):
        for seconds in (0, -1, 60.01, float("nan"), float("inf")):
            with self.subTest(seconds=seconds), self.assertRaises(SafetyError):
                self.observation(FakeWin32(), seconds, [])

    def test_cli_rejects_watch_with_input_or_without_capture_before_native_access(self):
        invalid = [
            ["crash", "--watch-seconds", "10"],
            ["crash", "--watch-seconds", "nan", "--capture-client"],
            ["crash", "--watch-seconds", "10", "--capture-client",
             "--action", "menu", "--vk", "0x0D", "--execute"],
        ]
        for args in invalid:
            with self.subTest(args=args), patch("tools.windows.operator_harness.Win32") as native, \
                    patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(main(args), 2)
                native.assert_not_called()

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
