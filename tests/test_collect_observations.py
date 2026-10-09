"""Bounded collector fixtures + actual UDP loopback, never original gameplay."""
from dataclasses import replace
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest

from integration.observation_alignment import Binding,Reason,descriptor
from integration.world_snapshot import CRASH,MARIO,encode
from tools.collect_observations import PairedObserver,receive,read_config,MAX_ATTEMPTS
from tests.test_observation_alignment import pose,frame


def observer():
    return PairedObserver({e:Binding(pose(e).session,frame(e)) for e in (CRASH,MARIO)},
        clock_id='single-test-receiver',max_age_ns=100,max_gap_ns=200)
def feed(o,e=CRASH,t=0,**changes): return o.accept(encode(pose(e,**changes)),t)

class CollectorTests(unittest.TestCase):
    def test_real_loopback_two_engines_one_receipt_clock(self):
        o=observer()
        output=io.StringIO()
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as receiver, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
            receiver.bind(('127.0.0.1',0))
            for e in (CRASH,MARIO):
                sender.sendto(encode(pose(e,native_tick=2**32-1 if e==CRASH else 0)),receiver.getsockname())
            summary=receive(receiver,o,output,seconds=1,max_packets=2)
        rows=[json.loads(line) for line in output.getvalue().splitlines()]
        arrivals=[r for r in rows if r['kind']=='arrival']
        self.assertEqual(len(arrivals),2)
        self.assertEqual(summary['sources']['1']['accepted'],1)
        self.assertEqual(summary['sources']['2']['accepted'],1)
        self.assertEqual({r['receiver_clock_id'] for r in rows},{o.alignment.clock_id})
        times=[r['receiver_monotonic_ns'] for r in rows]
        self.assertEqual(times,sorted(times))
        self.assertEqual({r['observed']['engine'] for r in arrivals},{CRASH,MARIO})
        self.assertTrue(all(r['physical_status']=='BLOCKED' and not r['calibration_ready'] for r in rows))
        self.assertTrue(all(r['source_delay']=='UNKNOWN' for r in rows))

    def test_sequence_holes_out_of_order_and_ticks_do_not_align(self):
        o=observer()
        self.assertEqual(feed(o,sequence=3,native_tick=2**32-1)['sequence_holes'],2)
        self.assertEqual(feed(o,t=1,sequence=5,native_tick=0)['sequence_holes'],1)
        self.assertEqual(feed(o,t=2,sequence=4)['reason'],Reason.REPLAY.value)
        feed(o,MARIO,3,native_tick=700)
        self.assertTrue(o.status(3)['telemetry_comparable'])
        self.assertEqual(o.sources[CRASH]['sequence_holes'],3)
        self.assertEqual(o.status(3)['receiver_arrival_separation_ns'],2)
        self.assertFalse(o.summary()['live_gameplay_verified'])

    def test_timeout_without_datagrams_and_bounded_idle_status(self):
        class Idle:
            def getsockname(self): return ('127.0.0.1',12345)
            def settimeout(self,t): pass
            def recvfrom(self,n): raise socket.timeout()
        o=observer()
        feed(o)
        stamps=iter((0,0,101,1_000_000_000,1_000_000_000))
        output=io.StringIO()
        receive(Idle(),o,output,seconds=1,max_packets=2,clock=lambda:next(stamps))
        rows=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[1]['sources'][0]['reason'],Reason.TIMEOUT.value)
        self.assertEqual(rows[1]['sources'][1]['reason'],Reason.MISSING.value)
        self.assertFalse(rows[1]['telemetry_comparable'])

    def test_pause_transition_and_explicit_rebind_preserve_independence(self):
        o=observer()
        feed(o,MARIO)
        self.assertEqual(feed(o,paused=True)['reason'],Reason.PAUSED.value)
        self.assertEqual(feed(o,t=1,sequence=2)['reason'],Reason.PAUSED.value)
        self.assertFalse(o.status(1)['telemetry_comparable'])
        o.rebind(CRASH,Binding(pose(CRASH).session,frame(CRASH,2)))
        self.assertEqual(feed(o,t=2,sequence=2,frame=frame(CRASH,2))['reason'],Reason.ACCEPTED.value)
        self.assertEqual(o.sources[CRASH]['sequence_holes'],0)
        # Mario changes area/epoch independently; current Crash is unaffected.
        import struct
        changed=struct.pack('!4shhII',b'M31A',16,2,0,2)
        row=feed(o,MARIO,3,sequence=2,frame=changed)
        self.assertEqual(row['reason'],Reason.FRAME.value)
        self.assertEqual(row['observed']['identity']['area'],2)
        self.assertEqual(o.status(3)['sources'][0]['reason'],Reason.ACCEPTED.value)
        o.rebind(MARIO,Binding(pose(MARIO).session,changed))
        self.assertTrue(feed(o,MARIO,4,sequence=2,frame=changed)['accepted'])

    def test_gap_clock_and_invalid_source_diagnostics(self):
        o=observer()
        feed(o)
        row=feed(o,t=201,sequence=2)
        self.assertEqual(row['reason'],Reason.GAP.value)
        self.assertEqual(row['since_last_accepted_ns'],201)
        self.assertEqual(feed(o,t=200,sequence=3)['reason'],Reason.CLOCK.value)
        self.assertEqual(o.accept(b'bad',202)['reason'],Reason.MALFORMED.value)
        self.assertEqual(feed(o,t=203,session=b'x'*16)['reason'],Reason.SESSION.value)
        self.assertEqual(o.accept(encode(pose(MARIO)),204,peer='192.0.2.1')['reason'],Reason.MALFORMED.value)
        self.assertEqual(feed(o,t=206,sequence=3,phase=2)['reason'],Reason.PHASE.value)
        self.assertNotIn('snapshot',row)

    def test_fresh_session_resets_only_sequence_and_arrival_baseline(self):
        o=observer()
        feed(o,sequence=99)
        feed(o,MARIO,0)
        o.rebind(CRASH,Binding(b'n'*16,frame(CRASH)))
        row=feed(o,t=1,session=b'n'*16)
        self.assertEqual(row['sequence_holes'],0)
        self.assertIsNone(row['receiver_arrival_gap_ns'])
        self.assertEqual(o.sources[MARIO]['accepted'],1)
        self.assertTrue(o.status(1)['telemetry_comparable'])

    def test_attempt_and_memory_bound(self):
        o=observer()
        packet=encode(pose(CRASH))
        for n in range(MAX_ATTEMPTS): o.accept(packet,n)
        with self.assertRaises(ValueError): o.accept(packet,MAX_ATTEMPTS)
        self.assertEqual(len(o.alignment.store.slots),1)
        self.assertEqual(len(o.sources),2)
        self.assertEqual(len(o.rejections),len(Reason)-1)
        self.assertEqual(o.attempts,MAX_ATTEMPTS)

    def test_malformed_configuration_and_descriptor_fail_with_value_error(self):
        good=dict(schema_version=1,max_age_ns=100,max_gap_ns=200,sources={
            name:dict(session=pose(e).session.hex(),frame=frame(e).hex())
            for name,e in (('crash',CRASH),('mario',MARIO))})
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'config.json'
            p.write_text(json.dumps(good))
            bindings,age,gap=read_config(p)
            self.assertNotEqual(bindings[CRASH].session,bindings[MARIO].session)
            for data in (' '*4097,'[]',json.dumps(dict(good,schema_version=True))):
                p.write_text(data)
                with self.assertRaises(ValueError): read_config(p)
        for e,f in ((CRASH,b'bad'),(99,frame(CRASH)),(MARIO,[])):
            with self.assertRaises(ValueError): descriptor(e,f)
        with self.assertRaises(ValueError): observer().rebind(CRASH,Binding(b'n'*16,b'bad'))

    def test_receiver_budget_loopback_and_windows_oversize_handling(self):
        class Oversize:
            def getsockname(self): return ('127.0.0.1',12345)
            def settimeout(self,t): pass
            def recvfrom(self,n):
                error=OSError('oversize')
                error.winerror=10040
                raise error
        output=io.StringIO()
        summary=receive(Oversize(),observer(),output,seconds=1,max_packets=1)
        self.assertEqual(summary['rejection_counts'][Reason.MALFORMED.value],1)
        self.assertEqual(summary['attempts'],1)
        for seconds,count in ((0,1),(301,1),(1,0),(1,10001),(True,1)):
            with self.assertRaises(ValueError): receive(Oversize(),observer(),io.StringIO(),seconds=seconds,max_packets=count)
        class Remote(Oversize):
            def getsockname(self): return ('0.0.0.0',12345)
        with self.assertRaises(ValueError): receive(Remote(),observer(),io.StringIO(),seconds=1,max_packets=1)

if __name__=='__main__': unittest.main()
