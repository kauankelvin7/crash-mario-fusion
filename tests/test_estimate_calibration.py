"""Synthetic mathematical proofs only; no native-frame/gameplay claim."""
from dataclasses import replace,asdict
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.estimate_calibration import (LandmarkPair,FitPolicy,estimate,estimate_document,SYNTHETIC,OPERATOR)
from tools.world_coordinates import FrameMap,encode_crash

POLICY=FitPolicy(.001,.001,10,10,.001,.001,True)
POSITIONS=((0,0,0),(100,20,0),(0,-10,100),(100,0,100),(25,50,75))

def pairs(mapping=None):
    mapping=mapping or FrameMap((0,0,0),(10,20,-30),2,90)
    return [LandmarkPair(f'SYNTHETIC-point-{i}',encode_crash(p),mapping.to_mario(p),
                        9,1,16,1,7,SYNTHETIC,True) for i,p in enumerate(POSITIONS)]

def fitted(items=None,policy=POLICY):
    items=items or pairs()
    return estimate(items[:3],items[3:],policy)

class CalibrationTests(unittest.TestCase):
    def test_known_scale_yaw_origin_and_independent_holdout(self):
        for yaw in (90,-90,37,-37,0,179):
            mapping=FrameMap((17,23,-9),(10,20,-30),2,yaw)
            result=fitted(pairs(mapping))
            self.assertAlmostEqual(result.frame_map.scale,2,places=6)
            self.assertAlmostEqual(result.frame_map.yaw_degrees,yaw,places=5)
            for point in POSITIONS:
                for a,b in zip(result.frame_map.to_mario(point),mapping.to_mario(point)):
                    self.assertAlmostEqual(a,b,places=3)
            self.assertLess(result.holdout.maximum,.001)
            self.assertLessEqual(result.maximum_inverse_error,1/512)
            self.assertFalse(result.calibration_ready)
            self.assertEqual(result.physical_status,'BLOCKED')
            self.assertEqual(result.interpretation,'SYNTHETIC_MATH_ESTIMATE_ONLY')
        result=fitted()
        self.assertAlmostEqual(result.frame_map.to_mario((0,0,0))[1],20)
        self.assertAlmostEqual(result.frame_map.to_mario((0,10,0))[1],40)

    def test_y_contributes_to_uniform_scale(self):
        ps=pairs()
        # Changing Y alone perturbs optimal scale; fitting is not an XZ-only shortcut.
        ps=[replace(p,mario_position=(p.mario_position[0],p.mario_position[1]*1.1,p.mario_position[2])) for p in ps]
        permissive=replace(POLICY,max_error=100,rms_error=100)
        self.assertGreater(fitted(ps,permissive).frame_map.scale,2)

    def test_insufficient_repeated_and_collinear(self):
        ps=pairs()
        for fit,holdout in ((ps[:2],ps[3:]),(ps[:3],[]),([ps[0],ps[0],ps[2]],ps[3:])):
            with self.assertRaises(ValueError): estimate(fit,holdout,POLICY)
        ps[1]=replace(ps[1],crash_raw=ps[0].crash_raw)
        with self.assertRaises(ValueError): fitted(ps)
        ps=pairs()
        ps[1]=replace(ps[1],mario_position=ps[0].mario_position)
        with self.assertRaises(ValueError): fitted(ps)
        ps=pairs()
        ps[2]=replace(ps[2],crash_raw=encode_crash((200,40,0)))
        with self.assertRaises(ValueError): fitted(ps)
        ps=pairs()
        ps[2]=replace(ps[2],mario_position=(10,100,-430))
        with self.assertRaises(ValueError): fitted(ps)

    def test_condition_and_baseline_fail_closed(self):
        with self.assertRaises(ValueError): fitted(policy=replace(POLICY,min_crash_xz_baseline=1000))
        with self.assertRaises(ValueError): fitted(policy=replace(POLICY,min_mario_xz_baseline=1000))
        with self.assertRaises(ValueError): fitted(policy=replace(POLICY,min_condition_ratio=.99))
        ps=pairs()
        ps[2]=replace(ps[2],crash_raw=encode_crash((200,0,1/256)))
        with self.assertRaises(ValueError): fitted(ps)

    def test_frame_scope_and_provenance_not_assumed(self):
        for field,value in (('crash_level',10),('crash_epoch',2),('mario_level',17),
                            ('mario_area',2),('mario_epoch',8),('provenance',OPERATOR)):
            ps=pairs()
            ps[-1]=replace(ps[-1],**{field:value})
            with self.assertRaises(ValueError): fitted(ps)
        for change in ({'correspondence_declared':False},{'label':''},{'crash_epoch':0},
                       {'mario_area':True},{'provenance':'REAL_VERIFIED'}):
            with self.assertRaises(ValueError): replace(pairs()[0],**change)
        ps=[replace(p,provenance=OPERATOR,label=f'operator-mark-{i}') for i,p in enumerate(pairs())]
        self.assertEqual(fitted(ps).interpretation,OPERATOR)
        self.assertFalse(fitted(ps).calibration_ready)

    def test_outliers_false_pairs_and_rms_have_no_trimming(self):
        for index in (0,4):
            ps=pairs()
            p=ps[index]
            ps[index]=replace(p,mario_position=(p.mario_position[0]+30,*p.mario_position[1:]))
            with self.assertRaises(ValueError): fitted(ps)
        ps=pairs()
        ps[0]=replace(ps[0],mario_position=ps[1].mario_position)
        ps[1]=replace(ps[1],mario_position=pairs()[0].mario_position)
        with self.assertRaises(ValueError): fitted(ps)
        ps=pairs()
        p=ps[-1]
        ps[-1]=replace(p,mario_position=(p.mario_position[0]+.1,*p.mario_position[1:]))
        with self.assertRaises(ValueError): fitted(ps,replace(POLICY,max_error=1,rms_error=.001))

    def test_negative_or_zero_uniform_scale_rejected(self):
        # XZ implies +2 but strong inverted Y makes the unconstrained uniform fit negative.
        ps=pairs()
        ps=[replace(p,mario_position=(p.mario_position[0],-100*p.crash_raw[1]/256,p.mario_position[2])) for p in ps]
        with self.assertRaises(ValueError): fitted(ps)
        for scale in (0,-1,math.nan,math.inf,True):
            with self.assertRaises(ValueError): FrameMap((0,0,0),(0,0,0),scale,0)

    def test_numeric_fixed_point_float32_inverse_and_native_bounds(self):
        for raw in ((2**31,0,0),(-(2**31)-1,0,0),(True,0,0)):
            with self.assertRaises(ValueError): replace(pairs()[0],crash_raw=raw)
        for target in ((math.nan,0,0),(1e39,0,0),(8192,0,0),(0,32768,0),(0,0,-8192)):
            ps=pairs()
            with self.assertRaises(ValueError):
                ps[-1]=replace(ps[-1],mario_position=target)
                fitted(ps)
        ps=pairs()
        ps[-1]=replace(ps[-1],mario_position=(160.00000001,120,-80))
        with self.assertRaises(ValueError): fitted(ps,replace(POLICY,max_target_quantization_error=1e-10))
        # A tiny scale maps valid s32 source positions but target quantization loses fixed-point bits.
        big=((8_000_000,0,0),(8_000_100,20,0),(8_000_000,-10,100),(8_000_100,0,100))
        ps=[LandmarkPair(str(i),encode_crash(p),(100+(p[0]-8_000_000)*1e-6,p[1]*1e-6,p[2]*1e-6),
                         9,1,16,1,7,SYNTHETIC,True) for i,p in enumerate(big)]
        with self.assertRaises(ValueError): estimate(ps[:3],ps[3:],replace(POLICY,min_mario_xz_baseline=1e-8))

    def test_policy_memory_limits_and_no_holdout_gate(self):
        for name in ('max_error','rms_error','min_crash_xz_baseline','min_mario_xz_baseline',
                     'min_condition_ratio','max_target_quantization_error'):
            for v in (0,-1,math.nan,math.inf,True):
                with self.assertRaises(ValueError): replace(POLICY,**{name:v})
        with self.assertRaises(ValueError): replace(POLICY,min_condition_ratio=2)
        with self.assertRaises(ValueError): replace(POLICY,require_holdout=1)
        with self.assertRaises(ValueError): estimate(pairs()*26,[],replace(POLICY,require_holdout=False))
        result=estimate(pairs()[:3],[],replace(POLICY,require_holdout=False))
        self.assertIn('No independent holdout supplied',result.gates)
        self.assertFalse(result.calibration_ready)

    def test_cli_fixture_and_bounded_input(self):
        fixture=Path(__file__).parent/'fixtures/calibration_landmarks_synthetic.json'
        result=estimate_document(json.loads(fixture.read_text()))
        self.assertAlmostEqual(result.frame_map.scale,2)
        command=[sys.executable,'-m','tools.estimate_calibration','--input']
        output=subprocess.run(command+[str(fixture)],capture_output=True,text=True,check=True)
        report=json.loads(output.stdout)
        self.assertFalse(report['calibration_ready'])
        self.assertEqual(report['interpretation'],'SYNTHETIC_MATH_ESTIMATE_ONLY')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'oversize.json'
            path.write_bytes(b' '*131073)
            output=subprocess.run(command+[str(path)],capture_output=True,text=True)
            self.assertNotEqual(output.returncode,0)
            self.assertIn('128 KiB',output.stderr)

if __name__=='__main__': unittest.main()
