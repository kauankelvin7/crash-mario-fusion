import copy
import unittest
from pathlib import Path
from tools.m43_live_gate import audit, RESERVED, source_gate
from unittest.mock import patch
from tempfile import TemporaryDirectory
from tools.prepare_m43_host import prepare

ROOT = Path(__file__).resolve().parents[1]

def fixture():
    rows = []
    for tick in range(1, 121):
        height = (tick - 40) * 10 if 40 < tick <= 50 else (60 - tick) * 10 if 50 < tick < 60 else 0
        rows.append(dict(schema=1, tick=tick, hostFrame=tick * 2, timestamp=tick * 100,
                         frequency=3000, sequence=tick, epoch=1, actorEpoch=1, x=tick, y=height, z=tick,
                         vx=1, vy=10 if 40 < tick < 50 else -10 if 50 <= tick < 60 else 0,
                         vz=1, action=0, stickX=1, stickY=0, jump=tick == 41,
                         surface="AUTHORED_NOT_CRASH"))
    return rows

class LiveControlsTests(unittest.TestCase):
    def test_synthetic_oracle_not_human_certification(self):
        result = audit(fixture())
        self.assertTrue(result["passed"])
        self.assertEqual(result["human_playability"], "NOT_CERTIFIED")
        self.assertFalse(result["authentic_crash_collision"])

    def test_spawn_fall_is_not_jump(self):
        rows = fixture()
        for row in rows:
            row["jump"] = False
        self.assertFalse(audit(rows)["passed"])

    def test_no_movement_fails(self):
        rows = fixture()
        for row in rows:
            row["x"] = row["z"] = 0
        self.assertFalse(audit(rows)["passed"])

    def test_epoch_reset_cannot_land_previous_jump(self):
        rows = fixture()
        for row in rows[50:]:
            row["epoch"] = 2
        self.assertFalse(audit(rows)["passed"])

    def test_reject_bad_evidence(self):
        for field, value in [("x", float("nan")), ("surface", "CRASH"), ("sequence", 0), ("timestamp", 1)]:
            rows = copy.deepcopy(fixture())
            rows[50][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit(rows)

    def test_actor_reset_cannot_fabricate_jump_landing(self):
        rows = fixture()
        for row in rows[50:]:
            row['actorEpoch'] = 2
        self.assertFalse(audit(rows)['passed'])

    def test_bounded_ticks(self):
        with self.assertRaises(ValueError):
            audit(fixture()[:20])

    def test_wrong_source_pin_fails_closed(self):
        with patch('tools.m43_live_gate.subprocess.check_output', return_value='wrong'):
            with self.assertRaises(ValueError):
                source_gate(ROOT)

    def test_wrong_cadence_fails(self):
        rows = fixture()
        for row in rows:
            row['timestamp'] *= 2
        self.assertFalse(audit(rows)['passed'])

    def test_host_patch_refuses_upstream_edits(self):
        with patch('tools.prepare_m43_host.source_gate'), self.assertRaises(ValueError):
            prepare(ROOT, ROOT)

    def test_private_host_exact_and_no_overwrite(self):
        with TemporaryDirectory() as temporary, patch('tools.prepare_m43_host.source_gate'), patch('tools.prepare_m43_host.verify_atlas'):
            target = Path(temporary)
            path = target / 'RecompOne.Runtime/Host/Window/OriginalMarioInputHost.cs'
            path.parent.mkdir(parents=True)
            prepare(ROOT, target)
            self.assertEqual(path.read_bytes(), (ROOT / 'integration/embedded_mario/OriginalMarioInputHost.cs').read_bytes())
            prepare(ROOT, target, True)
            path.write_text('private user edit')
            with self.assertRaises(ValueError):
                prepare(ROOT, target)
            self.assertEqual(path.read_text(), 'private user edit')

    def test_private_host_missing_verify_fails(self):
        with TemporaryDirectory() as temporary, patch('tools.prepare_m43_host.source_gate'), patch('tools.prepare_m43_host.verify_atlas'):
            with self.assertRaises(ValueError):
                prepare(ROOT, Path(temporary), True)

    def test_source_ownership_and_smoke_split(self):
        folder = ROOT / "integration/embedded_mario"
        capture = (folder / "LiveMarioControls.cs").read_text()
        mod = (folder / "CrashEmbeddedMarioMod.cs").read_text()
        overlay = (folder / "OriginalMarioOutputOverlay.cs").read_text()
        self.assertIn("LiveMarioControls.Capture();", overlay)
        self.assertNotIn("ImGui.", mod)
        for forbidden in ("GetAsyncKeyState", "WriteU32", "WriteU16", "host.Buttons ="):
            self.assertNotIn(forbidden, capture + mod)
        self.assertIn("ConfigManager.Game.Keys2", capture)
        self.assertIn("if (!live && ticks == 180)", mod)
        self.assertIn('CM64_LIVE_CONTROLS', mod)
        self.assertNotIn("ShiftRight", RESERVED)
        self.assertIn("lock (nativeLock)", mod)
        self.assertIn("cx=cy=cz=0;", overlay)
        self.assertIn("M43 AUTHORED FLOOR (not Crash collision)", overlay)

if __name__ == "__main__":
    unittest.main()
