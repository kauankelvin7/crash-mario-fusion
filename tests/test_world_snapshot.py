from dataclasses import replace
import math
import struct
import unittest

from integration.world_snapshot import (CRASH,MARIO,Snapshot,SnapshotStore,
    POST_CRASH_PHYSICS,POST_MARIO_UPDATE,encode,decode,HEADER)

SESSION=b"s"*16
FRAMES={CRASH:b"c"*16,MARIO:b"m"*16}


def fixture(engine=CRASH,**changes):
    snapshot=Snapshot(engine,POST_CRASH_PHYSICS if engine==CRASH else POST_MARIO_UPDATE,
        SESSION,FRAMES[engine],1,2,(-257,512,513) if engine==CRASH else (1.25,2.5,-3.75),
        (-1,2048,4095) if engine==CRASH else (-32768,0,32767),3,8)
    return replace(snapshot,**changes)


class SnapshotTests(unittest.TestCase):
    def test_native_wire_roundtrip_and_engine_local_ticks(self):
        for engine,size in ((CRASH,80),(MARIO,74)):
            value=fixture(engine,native_tick=2**32-1)
            packet=encode(value)
            self.assertEqual(len(packet),size)
            self.assertEqual(decode(packet),value)
            self.assertEqual(packet[:4],b"CMW1")
            self.assertEqual(struct.unpack_from("!I",packet,HEADER.size-4)[0],2**32-1)

    def test_malformed_payload_and_nonfinite_values_fail_closed(self):
        packet=encode(fixture(MARIO))
        for bad in (packet[:-1],packet+b"0",b"bad!"+packet[4:],packet[:6]+b"\0\2"+packet[8:],
                    packet[:HEADER.size]+struct.pack("!f",math.nan)+packet[HEADER.size+4:]):
            with self.assertRaises(ValueError): decode(bad)
        for changes in (dict(sequence=0),dict(state=True),dict(position=(True,0,0)),
                        dict(phase=POST_MARIO_UPDATE),dict(session=b"\0"*16),dict(rotation=(0,0,2**31))):
            with self.assertRaises(ValueError): encode(fixture(**changes))
        with self.assertRaises(ValueError): encode(fixture(MARIO,position=(1e39,0,0)))

    def test_deterministic_duplicates_session_frame_pause_and_expiry(self):
        store=SnapshotStore(SESSION,FRAMES,100)
        self.assertTrue(store.accept(encode(fixture()),1000))
        self.assertFalse(store.accept(encode(fixture()),1001))
        self.assertFalse(store.accept(encode(fixture(sequence=2,frame=b"x"*16)),1002))
        self.assertFalse(store.accept(encode(fixture(sequence=2,session=b"x"*16)),1003))
        self.assertEqual(store.latest(CRASH,1100).sequence,1)
        self.assertIsNone(store.latest(CRASH,1101))
        self.assertTrue(store.accept(encode(fixture(sequence=2,paused=True,native_tick=0)),1102))
        self.assertIsNone(store.latest(CRASH,1102))
        self.assertTrue(store.accept(encode(fixture(sequence=3,native_tick=1)),1103))
        self.assertEqual(store.latest(CRASH,1103).sequence,3)
        with self.assertRaises(ValueError): store.latest(CRASH,1000)
        with self.assertRaises(ValueError): store.accept(encode(fixture(sequence=4)),1000)

    def test_memory_is_bounded_and_generations_do_not_replay(self):
        store=SnapshotStore(SESSION,FRAMES,100)
        for seq in range(1,1001):
            for engine in (CRASH,MARIO):
                self.assertTrue(store.accept(encode(fixture(engine,sequence=seq)),seq))
        self.assertEqual(len(store.slots),2)
        changed=SnapshotStore(SESSION,{CRASH:b"n"*16,MARIO:FRAMES[MARIO]},100)
        self.assertFalse(changed.accept(encode(fixture(sequence=1001)),1001))
        self.assertIsNone(changed.latest(CRASH,1001))


if __name__=="__main__": unittest.main()
