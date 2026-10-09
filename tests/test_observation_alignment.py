"""Synthetic CMW1 arrivals, never a runtime synchronization result."""
from dataclasses import replace
import struct
import unittest
from integration.world_snapshot import CRASH,MARIO,Snapshot,encode
from integration.observation_alignment import Binding,ObservationAlignment,Reason

CLOCK='one-receiver'
def frame(engine,epoch=1,level=None):
    return (struct.pack('!4sIII',b'M32D',9 if level is None else level,epoch,0) if engine==CRASH
            else struct.pack('!4shhII',b'M31A',16 if level is None else level,1,0,epoch))
def pose(engine,**changes):
    return replace(Snapshot(engine,0 if engine==CRASH else 1,bytes([engine])*16,
        frame(engine),1,0,(0,0,0),(0,0,0),0,0),**changes)
def alignment():
    return ObservationAlignment({e:Binding(pose(e).session,frame(e)) for e in (CRASH,MARIO)},
        receiver_clock_id=CLOCK,max_age_ns=100,max_gap_ns=200)
def accept(a,p,t): return a.accept(encode(p),t,receiver_clock_id=CLOCK)
def view(a,t): return a.evaluate(t,receiver_clock_id=CLOCK)

class AlignmentTests(unittest.TestCase):
    def test_independent_sessions_frames_ticks_and_bounded_memory(self):
        a=alignment()
        self.assertEqual(view(a,0).sources[0].reason,Reason.MISSING)
        for seq in range(1,1001):
            self.assertTrue(accept(a,pose(CRASH,sequence=seq,native_tick=2**32-1 if seq%2 else 0),seq*2).accepted)
            self.assertTrue(accept(a,pose(MARIO,sequence=seq,native_tick=7),seq*2+1).accepted)
        result=view(a,2001)
        self.assertTrue(result.telemetry_comparable)
        self.assertEqual(result.receiver_arrival_separation_ns,1)
        self.assertEqual(result.physical_status,'BLOCKED')
        self.assertFalse(result.calibration_ready)
        self.assertEqual(len(a.store.slots),2)
        self.assertEqual(len(a.sequences),2)

    def test_malformed_session_replay_phase_and_clock(self):
        a=alignment()
        self.assertEqual(a.accept(b'bad',0,receiver_clock_id=CLOCK).reason,Reason.MALFORMED)
        self.assertEqual(accept(a,pose(CRASH,session=b'x'*16),1).reason,Reason.SESSION)
        self.assertEqual(accept(a,pose(CRASH,phase=2),2).reason,Reason.PHASE)
        self.assertTrue(accept(a,pose(CRASH,sequence=3),3).accepted)
        for seq in (3,2,1): self.assertEqual(accept(a,pose(CRASH,sequence=seq),4).reason,Reason.REPLAY)
        self.assertEqual(accept(a,pose(CRASH,sequence=4),3).reason,Reason.CLOCK)
        self.assertEqual(a.accept(encode(pose(MARIO)),5,receiver_clock_id='collector-B').reason,Reason.DOMAIN)
        self.assertFalse(a.evaluate(3,receiver_clock_id=CLOCK).telemetry_comparable)

    def test_pause_requires_explicit_new_epoch_and_no_sequence_reset(self):
        a=alignment()
        self.assertEqual(accept(a,pose(CRASH,paused=True),1).reason,Reason.PAUSED)
        self.assertEqual(accept(a,pose(CRASH,sequence=2),2).reason,Reason.PAUSED)
        self.assertEqual(view(a,2).sources[0].reason,Reason.PAUSED)
        with self.assertRaises(ValueError): a.rebind(CRASH,a.bindings[CRASH])
        a.rebind(CRASH,Binding(pose(CRASH).session,frame(CRASH,2)))
        self.assertEqual(accept(a,pose(CRASH,frame=frame(CRASH,2)),3).reason,Reason.REPLAY)
        self.assertTrue(accept(a,pose(CRASH,frame=frame(CRASH,2),sequence=2),4).accepted)
        a.rebind(CRASH,Binding(b'n'*16,frame(CRASH,1)))
        self.assertTrue(accept(a,pose(CRASH,session=b'n'*16),5).accepted)

    def test_frame_changes_invalidate_only_that_source(self):
        a=alignment()
        for e in (CRASH,MARIO): accept(a,pose(e),0)
        self.assertEqual(accept(a,pose(CRASH,sequence=2,frame=frame(CRASH,2,10)),1).reason,Reason.FRAME)
        v=view(a,1)
        self.assertEqual(v.sources[0].reason,Reason.FRAME)
        self.assertEqual(v.sources[1].reason,Reason.ACCEPTED)
        a.rebind(CRASH,Binding(pose(CRASH).session,frame(CRASH,2,10)))
        self.assertTrue(accept(a,pose(CRASH,sequence=2,frame=frame(CRASH,2,10)),2).accepted)
        self.assertEqual(accept(a,pose(CRASH,sequence=3,frame=frame(CRASH)),3).reason,Reason.FRAME)
        self.assertEqual(view(a,3).sources[0].reason,Reason.ACCEPTED)

    def test_timeout_gap_and_boundary(self):
        a=alignment()
        accept(a,pose(CRASH),0)
        self.assertEqual(view(a,100).sources[0].reason,Reason.ACCEPTED)
        self.assertEqual(view(a,101).sources[0].reason,Reason.TIMEOUT)
        self.assertEqual(accept(a,pose(CRASH,sequence=2),201).reason,Reason.GAP)
        self.assertEqual(accept(a,pose(CRASH,sequence=3),202).reason,Reason.GAP)
        a.rebind(CRASH,Binding(pose(CRASH).session,frame(CRASH,2)))
        self.assertTrue(accept(a,pose(CRASH,sequence=3,frame=frame(CRASH,2)),203).accepted)

    def test_configuration_and_identity_bounds(self):
        for age in (None,True,-1,0,10**9+1):
            with self.assertRaises(ValueError):
                ObservationAlignment(alignment().bindings,receiver_clock_id=CLOCK,max_age_ns=age,max_gap_ns=10**10)
        a=alignment()
        self.assertEqual(a.accept(encode(pose(CRASH,frame=b'x'*16)),0,receiver_clock_id=CLOCK).reason,Reason.MALFORMED)
        for stamp in (-1,True,2**64):
            self.assertEqual(a.accept(encode(pose(CRASH)),stamp,receiver_clock_id=CLOCK).reason,Reason.MALFORMED)

if __name__=='__main__': unittest.main()
