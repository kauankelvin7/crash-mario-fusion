"""Camera guest-RAM source observer synthetic contract tests (asset-free).

Original Sanity Beach Windows native proof is audited separately from private
host logs; these mocks never establish a calibrated 3D camera or full depth.
"""
from pathlib import Path
import unittest

from tools.assess_camera_probe import parse, assess

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"integration/embedded_mario/CrashCameraProbe.cs"

def row(seq=1,epoch=1,level=9,tx=123456,progress=128,matrix=None,
        phase="PAD_UNKNOWN",proj=288,zone="8009E758",path="800A2058"):
    m=matrix or (4096,0,-13,4,-2170,1359,-11,-2175,-3471)
    return (f"[cm64-camera] RAW_SAMPLE phase={phase} level={level} seq={seq}"
        f" epoch={epoch} projection={proj} zone=0x{zone} path=0x{path}"
        f" progress={progress} tx={tx} ty=65432 tz=235682"
        f" m={','.join(map(str,m))} changed=1 safe_for_shared_depth=false")

class CameraEvidence(unittest.TestCase):
    def test_raw_source_observer_accepts_valid_original_shape(self):
        r=parse(row())
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["level"],9)
        self.assertEqual(r[0]["proj"],288)
        self.assertEqual(r[0]["matrix"][0],4096)

    def test_consecutive_same_scope_native_variation_gate(self):
        rows=parse("\n".join([row(1,tx=100),row(2,tx=140,progress=160),
                              row(3,tx=190,progress=192)]))
        report=assess(rows)
        self.assertTrue(report["verified"])
        self.assertEqual(report["changed"],2)
        self.assertFalse(report["postphysics"])
        self.assertFalse(report["depth_complete"])
        self.assertFalse(report["camera_calibrated"])

    def test_stationary_majority_does_not_hide_a_scoped_valid_change(self):
        text="\n".join([row(1,tx=100),row(2,tx=120),row(3,tx=140)]+
                       [row(i,epoch=2,tx=140,progress=140) for i in range(4,15)])
        gate=assess(parse(text))
        self.assertTrue(gate["verified"])
        self.assertEqual(gate["scope_samples"],3)

    def test_stationary_or_only_two_native_frames_cannot_pass(self):
        self.assertFalse(assess(parse("\n".join(
            row(i,tx=100,progress=128) for i in range(1,6))))["verified"])
        self.assertFalse(assess(parse("\n".join(
            [row(1,tx=100),row(2,tx=120)])))["verified"])

    def test_level_zone_and_epoch_boundaries_never_merge_camera(self):
        rows=parse("\n".join([row(1,tx=100),row(2,tx=120),
                      row(3,epoch=2,tx=150),row(4,epoch=2,tx=200),
                      row(5,epoch=3,tx=250),row(6,epoch=3,tx=300)]))
        self.assertFalse(assess(rows)["verified"])

    def test_sample_sequence_must_never_regress(self):
        samples=parse("\n".join([row(2),row(1,tx=130),row(3,tx=160)]))
        with self.assertRaisesRegex(ValueError,"Nonmonotonic"):
            assess(samples)

    def test_reject_wrong_phase_or_calibration_claims(self):
        for text in [row(phase="POST_PHYSICS"),
                     row().replace("safe_for_shared_depth=false","safe_for_shared_depth=true")]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse(text)

    def test_reject_unbounded_camera_and_corrupt_matrix(self):
        for text in (row(proj=0),row(proj=4097),row(zone="9009E758"),
                     row(matrix=(4096,)*8),row(matrix=(50000,)*9),
                     row(matrix=(0,)*9)):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse(text)

    def test_source_reads_raw_ram_only_and_is_opt_in(self):
        s=SRC.read_text(encoding="utf-8")
        mod=(ROOT/"integration/embedded_mario/CrashEmbeddedMarioMod.cs").read_text(encoding="utf-8")
        for phrase in ("BinaryPrimitives.ReadUInt32LittleEndian",
                       "BinaryPrimitives.ReadInt16LittleEndian",
                       "m.Ram","PadReadEvent","phase=UNKNOWN_DIAGNOSTIC",
                       "safe_for_shared_depth=false","accepted>=48",
                       "now-startMs>90000","LevelKind.Gameplay"):
            self.assertIn(phrase,s)
        for address in ("0x800577E4u","0x80057864u","0x800578D0u",
                        "0x80057914u","0x8005791Cu"):
            self.assertIn(address,s)
        self.assertNotIn("m.ReadU32(",s)
        self.assertNotIn("m.Write",s)
        self.assertIn("CM64_CAMERA_PROBE",mod)
        self.assertIn("CrashCameraProbe.Stop()",mod)

    def test_private_pinned_build_and_game_runner(self):
        build=(ROOT/"tools/windows/Build-CameraProbe.ps1").read_text(encoding="utf-8")
        run=(ROOT/"tools/windows/Run-CameraProbe.ps1").read_text(encoding="utf-8")
        for s in (build,run):
            self.assertIn("CrashMarioFusion/M41B2B-camera",s)
            self.assertIn("CrashCameraProbe.cs",s)
            self.assertIn("Get-FileHash",s)
        self.assertIn("CM64_CAMERA_PROBE='1'",run)
        self.assertIn("tools.assess_camera_probe --private-log",run)
        self.assertIn("$ok=$ok -and $cameraEvidence",run)
        self.assertIn("Stop-Process -Id $p.Id",run)

if __name__=="__main__":
    unittest.main()
