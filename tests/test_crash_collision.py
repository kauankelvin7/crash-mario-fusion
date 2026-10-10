"""Authored telemetry only; no retail RAM, volumes or recordings in these tests."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.assess_crash_collision import BASE, C1_PIN, LAUNCHER_PIN, assess, validate


def fixture(sequence=1):
    return dict(version=1, sequence=sequence, epoch=1, level=9, path=BASE + 0x1000,
                actor=BASE + 0x2000, actorZone=BASE + 0x100, position=[sequence, 0, 0],
                source="C1_ZONE_ITEM1", phase="PAD_UNKNOWN", launcherPin=LAUNCHER_PIN,
                c1Pin=C1_PIN, originalQueryCorrelated=False, allocationGenerationKnown=False,
                neighborCoverage=False, materialMappingKnown=False, triangles=False,
                zone=dict(Entry=BASE + 0x100, Eid=123, EntryType=7, RectAddress=BASE + 0x240,
                          RectEnd=BASE + 0x280, Digest="a" * 64, Min=[0, 0, 0],
                          Max=[16384, 16384, 16384], Depths=[0, 0, 0],
                          Volumes=[dict(Node=3, Depth=0, Min=[0, 0, 0], Max=[16384] * 3)]))


class CollisionAuditTests(unittest.TestCase):
    def test_valid_diagnostic_does_not_pass_g1_or_allow_g2(self):
        result = assess([fixture(index) for index in range(1, 4)])
        self.assertTrue(result["diagnostic_observed"])
        self.assertFalse(result["g1_passed"])
        self.assertFalse(result["g2_allowed"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_stationary_and_short_traces_rejected(self):
        self.assertFalse(assess([fixture()])["diagnostic_observed"])
        records = [fixture(index) for index in range(1, 4)]
        for record in records:
            record["position"] = [0, 0, 0]
        self.assertEqual(assess(records)["reason"], "NO_STABLE_MOVING_SCENE")

    def test_stale_epoch_and_nonmonotonic_sequence(self):
        records = [fixture(index) for index in range(1, 4)]
        records[1]["zone"]["Digest"] = "b" * 64
        self.assertEqual(assess(records)["reason"], "STALE_SCENE_EPOCH")
        records = [fixture(index) for index in (1, 3, 2)]
        self.assertIn("NONMONOTONIC", assess(records)["reason"])

    def test_changed_scene_requires_new_stable_scope(self):
        records = [fixture(index) for index in range(1, 5)]
        for record in records[1:]:
            record["zone"]["Digest"] = "b" * 64
            record["epoch"] = 2
        self.assertTrue(assess(records)["diagnostic_observed"])

    def test_flags_cannot_promote_unknown_provenance(self):
        for name in ("triangles", "originalQueryCorrelated", "allocationGenerationKnown",
                     "neighborCoverage", "materialMappingKnown"):
            record = fixture(); record[name] = True
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate(record)

    def test_bad_pins_phases_types_bounds_and_capacities(self):
        changes = [("version", True), ("version", 1.0), ("level", 8), ("phase", "POSTPHYSICS"), ("c1Pin", "a" * 40),
                   ("sequence", True), ("actor", BASE + 0x1FFFF0), ("position", [0, 0])]
        for name, value in changes:
            record = fixture(); record[name] = value
            with self.subTest(name=name), self.assertRaises((ValueError, TypeError)):
                validate(record)
        for field, value in (("Digest", "bad"), ("Depths", [17, 0, 0]),
                             ("Max", [0, 0, 0]), ("Volumes", []), ("RectEnd", BASE + 0x200)):
            record = fixture(); record["zone"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(record)

    def test_volume_shape_and_duplicate_rejected(self):
        for change in ("duplicate", "outside", "even", "depth", "unaligned"):
            record = fixture()
            volume = record["zone"]["Volumes"][0]
            if change == "duplicate":
                record["zone"]["Volumes"].append(copy.deepcopy(volume))
            elif change == "outside": volume["Max"][0] += 1
            elif change == "even": volume["Node"] = 2
            elif change == "depth": volume["Depth"] = 1
            else: volume["Min"][0] = 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(record)

    def test_cli_fail_closed_without_printing_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "authored.log"
            log.write_text("\n".join("CM64_COLLISION " + json.dumps(fixture(index))
                                     for index in range(1, 4)), encoding="utf8")
            output = subprocess.run([sys.executable, "-m", "tools.assess_crash_collision",
                                     "--private-log", str(log)], capture_output=True, text=True)
            self.assertEqual(output.returncode, 2)
            self.assertTrue(json.loads(output.stdout)["diagnostic_observed"])
            self.assertNotIn("Volumes", output.stdout)

    def test_unrelated_oem_host_output_does_not_corrupt_utf8_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "authored-oem.log"
            protocol = "\n".join("CM64_COLLISION " + json.dumps(fixture(index))
                                  for index in range(1, 4))
            log.write_bytes(b"unrelated host OEM \x85\n" + protocol.encode("utf8"))
            output = subprocess.run([sys.executable, "-m", "tools.assess_crash_collision",
                                     "--private-log", str(log)], capture_output=True, text=True)
            self.assertEqual(output.returncode, 2)
            self.assertTrue(json.loads(output.stdout)["diagnostic_observed"])
            log.write_bytes(b"CM64_COLLISION \x85\n")
            output = subprocess.run([sys.executable, "-m", "tools.assess_crash_collision",
                                     "--private-log", str(log)], capture_output=True, text=True)
            self.assertEqual(output.returncode, 2)
            self.assertFalse(json.loads(output.stdout)["g1_passed"])


if __name__ == "__main__":
    unittest.main()
