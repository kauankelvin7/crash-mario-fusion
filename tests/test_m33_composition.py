"""Combined P1/P2/P3 scope, precision and geometry gates: authored data only."""
from dataclasses import replace
import json
from pathlib import Path
import struct
import unittest

from integration.observation_alignment import Binding,ObservationAlignment
from integration.world_snapshot import CRASH,MARIO,Snapshot,encode
from tools.estimate_calibration import estimate_document,OPERATOR
from tools.volume_boundary import AuthoredLeaf,estimated_top_boundary

FIXTURE=Path(__file__).parent/'fixtures/calibration_landmarks_synthetic.json'
CF=struct.pack('!4sIII',b'M32D',9,1,0)
MF=struct.pack('!4shhII',b'M31A',16,1,0,7)
MATERIAL=dict(provenance='AUTHORED_SYNTHETIC',native_type=0,room=0)

def preview(result,**changes):
    opts=dict(estimate=result,crash_frame=CF,mario_frame=MF,material=MATERIAL,
              surface_capacity=2,node_capacity=256,surfaces_used=0,nodes_used=0)
    opts.update(changes)
    return estimated_top_boundary(AuthoredLeaf((0,0,0),(16,16,16),'AUTHORED_C1_SINGLE_LEAF',3),**opts)

class CompositionTests(unittest.TestCase):
    def setUp(self): self.estimate=estimate_document(json.loads(FIXTURE.read_text()))

    def test_cmw_estimate_geometry_share_explicit_scope_not_physics(self):
        sessions={CRASH:b'c'*16,MARIO:b'm'*16}
        frames={CRASH:CF,MARIO:MF}
        alignment=ObservationAlignment({e:Binding(sessions[e],frames[e]) for e in sessions},
            receiver_clock_id='one',max_age_ns=100,max_gap_ns=200)
        for e in sessions:
            self.assertTrue(alignment.accept(encode(Snapshot(e,0 if e==CRASH else 1,sessions[e],
                frames[e],1,2**32-1 if e==CRASH else 7,(0,0,0),(0,0,0),0,0)),0,
                receiver_clock_id='one').accepted)
        comparison=alignment.evaluate(1,receiver_clock_id='one')
        result=preview(self.estimate)
        self.assertTrue(comparison.telemetry_comparable)
        self.assertFalse(result['calibration_ready'])
        self.assertEqual(result['physical_status'],'BLOCKED')
        self.assertFalse(result['live_collision_inserted'])
        self.assertEqual(result['scope'],self.estimate.scope)
        self.assertEqual(result['plan']['surfaces_required'],2)
        self.assertTrue(all(face['partition']=='floor' for face in result['plan']['surfaces']))

    def test_scope_changes_fail_closed_across_modules(self):
        for options in (dict(crash_frame=struct.pack('!4sIII',b'M32D',10,1,0)),
                        dict(crash_frame=struct.pack('!4sIII',b'M32D',9,2,0)),
                        dict(mario_frame=struct.pack('!4shhII',b'M31A',17,1,0,7)),
                        dict(mario_frame=struct.pack('!4shhII',b'M31A',16,2,0,7)),
                        dict(mario_frame=struct.pack('!4shhII',b'M31A',16,1,0,8)),
                        dict(mario_frame=b'bad')):
            with self.assertRaises(ValueError): preview(self.estimate,**options)
        for result in (replace(self.estimate,calibration_ready=True),
                       replace(self.estimate,interpretation=OPERATOR)):
            with self.assertRaises(ValueError): preview(result)

    def test_valid_math_does_not_override_s16_geometry_or_pool_gates(self):
        from tools.world_coordinates import FrameMap
        # Candidate math can represent poses; native triangle quantization is stricter.
        for mapping in (FrameMap((0,0,0),(10,20,-30),.004,90),
                        FrameMap((0,0,0),(10,32750,-30),2,90)):
            result=replace(self.estimate,frame_map=mapping)
            with self.assertRaises(ValueError): preview(result)
        with self.assertRaises(ValueError): preview(self.estimate,surface_capacity=1)
        with self.assertRaises(ValueError): preview(self.estimate,node_capacity=0)
        with self.assertRaises(ValueError): preview(self.estimate,material=dict(provenance='RETAIL',native_type=0,room=0))

if __name__=='__main__': unittest.main()
