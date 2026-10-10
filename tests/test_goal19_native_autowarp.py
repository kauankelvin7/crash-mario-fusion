"""Asset-free source constraints for original-game opt-in level warp, not gameplay proof."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Goal19NativeAutoWarpContracts(unittest.TestCase):
    def test_authentic_host_developer_warp_is_optional(self):
        s = (ROOT / "integration/embedded_mario/CrashEmbeddedMarioMod.cs").read_text()
        self.assertIn('Environment.GetEnvironmentVariable("CM64_GOAL19_NATIVE_AUTOWARP") == "1"', s)
        self.assertIn('CheatManager.RequestWarp(9, 1);', s)
        self.assertIn('&& (!live || !inOutput)', s)
        self.assertIn('native_scene_unverified=true', s)
        self.assertNotIn("Memory.WriteU32", s)
        self.assertNotIn("Dispatcher.Call(", s)

    def test_original_guest_level_observation_is_fail_closed(self):
        s = (ROOT / "integration/embedded_mario/LiveMarioControls.cs").read_text()
        self.assertIn("Catalog.Levels.TryGet(level, out var info)", s)
        self.assertIn("info.Kind == LevelKind.Gameplay", s)
        self.assertIn("ram.Slice(0x56400, 4)", s)
        self.assertIn("ram.Slice(0x5640C, 4)", s)
        self.assertIn("Interlocked.Exchange(ref optInLevelReceipt, 1) == 0", s)
        self.assertIn("level == 9 && Environment.GetEnvironmentVariable", s)
        self.assertIn("postphysics=false collision=false", s)

    def test_runner_requires_owned_media_human_approval_and_private_trace(self):
        s = (ROOT / "tools/windows/Test-Goal19NativeAutoWarp.ps1").read_text()
        self.assertIn("-ApproveHumanRun required", s)
        self.assertIn("Local\\CrashMarioFusion-OriginalGame", s)
        self.assertIn("Get-Process -Name 'CrashBandicoot*'", s)
        self.assertIn("M43-input/autowarp-", s)
        self.assertIn("CM64_GOAL19_NATIVE_AUTOWARP='1'", s)
        self.assertIn("GOAL19_AUTOWARP_PREFLIGHT_OK", s)
        self.assertIn("owned private Crash disc", s)
        self.assertIn("9bef1128717f958171a4afac3ed78ee2bb4e86ce", s)
        self.assertIn("CloseMainWindow()", s)
        self.assertIn("Stop-Process -Id $p.Id", s)
        self.assertIn("real_crash_collider=$false", s)
        self.assertIn("full_playable=$false", s)
        self.assertNotIn("Invoke-WebRequest", s)
        self.assertNotIn("git push", s)


if __name__ == "__main__":
    unittest.main()
