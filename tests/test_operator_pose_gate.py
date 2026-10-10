"""Source-only assertions for the opt-in original-runtime pose gate wrapper."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ManualPoseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "tools/windows/Run-PoseGate.ps1").read_text(encoding="utf-8")

    def test_preflight_and_explicit_original_runtime_choice(self):
        self.assertIn("[ValidateSet('Crash','Mario')]", self.text)
        self.assertIn("[switch]$CheckOnly", self.text)
        self.assertIn("if ($CheckOnly)", self.text)
        self.assertIn("exit 0", self.text)
        self.assertIn("checked_launcher", self.text)
        self.assertIn(".cm64-generated.json", self.text)
        self.assertIn("'-m','tools.collect_crash_pose'", self.text)
        self.assertIn("'-m','tools.collect_pose'", self.text)

    def test_bounded_read_only_diagnostics_and_no_commercial_copy(self):
        self.assertIn("[ValidateRange(30,300)]", self.text)
        self.assertIn("[ValidateRange(1,3000)]", self.text)
        self.assertIn("'--seconds'", self.text)
        self.assertIn("'--count'", self.text)
        self.assertIn("POSE_NOT_VERIFIED", self.text)
        self.assertIn("physical_status=BLOCKED", self.text)
        forbidden = ("CM64_APPLY", "-Apply", "SendKeys", "Copy-Item",
                     "Set-Content", "curl.exe", "Invoke-WebRequest", "git push")
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)


if __name__ == "__main__":
    unittest.main()
