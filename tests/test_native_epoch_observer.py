"""Source-only native observer epoch policy checks."""
import unittest
from integration.observation_alignment import Binding
from integration.world_snapshot import CRASH, MARIO, encode
from tests.test_observation_alignment import frame, pose
from tools.native_epoch_observer import NativeEpochObserver

class GateTests(unittest.TestCase):
    def mk(self):
        return NativeEpochObserver(
            {e: Binding(pose(e).session, frame(e)) for e in (CRASH, MARIO)},
            {CRASH: {9}, MARIO: {(6, 1), (16, 1)}},
            clock_id="local-receiver", max_age_ns=100, max_gap_ns=200)

    def test_native_epoch_change(self):
        o = self.mk()
        self.assertTrue(o.accept(encode(pose(CRASH)), 1)["accepted"])
        self.assertTrue(o.accept(encode(pose(CRASH, sequence=2,
            frame=frame(CRASH, 3))), 2)["accepted"])
        self.assertFalse(o.accept(encode(pose(CRASH, sequence=3,
            frame=frame(CRASH, 2))), 3)["accepted"])

    def test_first_allowed_mario_level_and_reject_wrong_session(self):
        o = self.mk()
        good = o.accept(encode(pose(MARIO, frame=frame(MARIO, level=6))), 1)
        self.assertTrue(good["accepted"])
        prior = o.alignment.bindings[MARIO].frame
        bad = o.accept(encode(pose(MARIO, frame=frame(MARIO, 3),
            session=b"x"*16, sequence=2)), 2)
        self.assertFalse(bad["accepted"])
        self.assertEqual(o.alignment.bindings[MARIO].frame, prior)

    def test_unknown_crash_level_never_rebinds(self):
        o = self.mk()
        bad = o.accept(encode(pose(CRASH, frame=frame(CRASH, 2, 10))), 1)
        self.assertFalse(bad["accepted"])
        self.assertEqual(o.alignment.bindings[CRASH].frame, frame(CRASH))

if __name__ == "__main__":
    unittest.main()
