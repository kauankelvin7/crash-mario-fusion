"""Asset-free consistency checks for a *recorded* Windows trace, not a new game run.

The fixture is a sanitized transcription of observed native-runtime output.
Passing these tests never upgrades cloud fixture replay to VERIFIED_REAL.
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRACE = ROOT / "tests" / "fixtures" / "windows_coin_jump_20261009.json"


class RecordedWindowsTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trace = json.loads(TRACE.read_text(encoding="utf-8"))

    def test_explicit_provenance_and_no_commercial_files(self):
        trace = self.trace
        self.assertEqual(trace["schema_version"], 1)
        self.assertEqual(trace["record_kind"], "SANITIZED_OPERATOR_TRANSCRIBED_REAL_TRACE")
        self.assertIn("not a fresh native-game execution", trace["verification_note"])
        self.assertIn("not a video capture", trace["human_observation"])
        self.assertNotIn("rom", trace["event_trace"])
        self.assertNotIn("disc", trace["event_trace"])
        self.assertFalse(any(TRACE.parent.glob("*.z64")))
        self.assertFalse(any(TRACE.parent.glob("*.bin")))

    def test_native_coin_sequences_correlate_with_crash_receipts(self):
        event = self.trace["event_trace"]
        self.assertTrue(event["keyboard_arm"])
        self.assertTrue(event["apply"])
        sent = event["mario_coins_sent"]
        received = event["crash_events"]
        self.assertEqual([x["seq"] for x in sent], [1, 2])
        self.assertEqual([x["seq"] for x in received], [1, 2])
        self.assertEqual([x["native_tick"] for x in sent],
                         [x["mario_tick"] for x in received])
        self.assertEqual([x["coin_count"] for x in sent],
                         [x["coin_count"] for x in received])
        self.assertTrue(all(x["bytes"] == 52 for x in sent))
        self.assertTrue(all(x["received"] for x in received))
        self.assertEqual([x["seq"] for x in received if x["input_applied"]], [1])
        self.assertEqual([x["seq"] for x in received if x.get("observe_only")], [2])

    def test_motion_summary_matches_recorded_native_samples(self):
        motion = self.trace["motion"]
        samples = motion["samples"]
        summary = motion["reported_summary"]
        self.assertTrue(motion["read_only"])
        self.assertEqual(motion["sequence"], 1)
        self.assertEqual(len(samples), 22)
        self.assertEqual([s["n"] for s in samples], list(range(1, 23)))
        self.assertEqual(summary["samples"], len(samples))
        y = [s["y_raw"] for s in samples]
        self.assertEqual(summary["y_start"], y[0])
        self.assertEqual(summary["y_min"], min(y))
        self.assertEqual(summary["y_max"], max(y))
        self.assertEqual(summary["y_last"], y[-1])
        self.assertEqual(summary["reason"], "window_complete")

    def test_guest_arc_is_consistent_with_rise_air_and_landing(self):
        samples = self.trace["motion"]["samples"]
        first, last = samples[0], samples[-1]
        self.assertTrue(first["groundland_flag"])
        self.assertFalse(first["air_flag"])
        airborne = [i for i, sample in enumerate(samples) if sample["air_flag"]]
        self.assertGreater(len(airborne), 2)
        self.assertGreater(max(s["y_raw"] for s in samples), first["y_raw"])
        self.assertTrue(any(samples[i]["vy_raw"] > 0 for i in airborne))
        self.assertTrue(any(samples[i]["vy_raw"] < 0 for i in airborne))
        self.assertTrue(any(s["groundland_flag"] and not s["air_flag"]
                            for s in samples[max(airborne) + 1:]))
        self.assertTrue(last["groundland_flag"])
        self.assertFalse(last["air_flag"])
        self.assertLessEqual(abs(last["y_raw"] - first["y_raw"]), 16)
        self.assertTrue(self.trace["motion"]["reported_summary"]["rise_and_landing_candidate"])

    def test_explicitly_unverified_shared_world(self):
        missing = set(self.trace["not_verified"])
        self.assertIn("shared collision", missing)
        self.assertIn("shared geometry", missing)
        self.assertIn("shared rendering or camera", missing)
        self.assertIn("cross-engine latency measurement", missing)


if __name__ == "__main__":
    unittest.main()
