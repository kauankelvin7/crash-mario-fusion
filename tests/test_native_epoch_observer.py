"""Source-only native observer epoch policy checks."""
import unittest
from integration.observation_alignment import Binding
from integration.world_snapshot import CRASH, MARIO, encode
from tests.test_observation_alignment import frame, pose
from tools.native_epoch_observer import NativeEpochObserver

class GateTests(unittest.TestCase):
    def test_native_epoch_change(self):
        o = NativeEpochObserver(
            {e: Binding(pose(e).session, frame(e)) for e in (CRASH, MARIO)},
            {CRASH: {9}, MARIO: {(6, 1), (16, 1)}},
            clock_id="local-receiver", max_age_ns=100, max_gap_ns=200)
        self.assertTrue(o.accept(encode(pose(CRASH)), 1)["accepted"])
        self.assertTrue(o.accept(encode(pose(CRASH, sequence=2,
            frame=frame(CRASH, 3))), 2)["accepted"])
        self.assertFalse(o.accept(encode(pose(CRASH, sequence=3,
            frame=frame(CRASH, 2))), 3)["accepted"])

if __name__ == "__main__":
    unittest.main()
