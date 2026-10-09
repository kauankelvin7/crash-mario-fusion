"""Synthetic diagnostic protocol checks, never evidence of real gameplay."""
from dataclasses import replace
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from integration.world_snapshot import Snapshot, CRASH, UNKNOWN_DIAGNOSTIC, encode, decode
from tools.collect_crash_pose import CrashCapture, frame_descriptor, checked_launcher, collect

SESSION = bytes.fromhex('00112233445566778899aabbccddeeff')


def frame(level=9, epoch=1, reserved=0):
    return struct.pack('!4sIII', b'M32D', level, epoch, reserved)


def sample(**kwargs):
    return replace(Snapshot(CRASH, UNKNOWN_DIAGNOSTIC, SESSION, frame(), 1, 1,
                            (-257, -2147483648, 513), (-1, 1024, 2147483647), 2, 8), **kwargs)


class CrashPoseTests(unittest.TestCase):
    def test_signed_wire_and_diagnostic_metadata(self):
        packet = encode(sample())
        self.assertEqual(len(packet), 80)
        self.assertEqual(decode(packet), sample())
        self.assertEqual(struct.unpack('!6iII', packet[48:]), (-257, -2147483648, 513, -1, 1024, 2147483647, 2, 8))
        row = CrashCapture(SESSION).accept(packet, 1)
        self.assertEqual(row['native_level'], 9)
        self.assertEqual(row['tick_kind'], 'observer_pad_callback')
        self.assertEqual(row['native_frame_generation'], 'unknown')
        self.assertFalse(row['calibration_ready'])

    def test_session_replay_tick_and_frame_conflict(self):
        capture = CrashCapture(SESSION)
        capture.accept(encode(sample()), 1)
        for bad in (sample(), sample(sequence=2), sample(sequence=2,native_tick=2,session=b'x'*16),
                    sample(sequence=2,native_tick=2,frame=frame(level=10)),
                    sample(sequence=2,native_tick=2,phase=2), sample(sequence=2,native_tick=2,phase=3)):
            self.assertIsNone(capture.accept(encode(bad), 2))
        self.assertIsNotNone(capture.accept(encode(sample(sequence=2,native_tick=2,frame=frame(10,2))),3))
        self.assertIsNone(capture.accept(encode(sample(sequence=3,native_tick=3)),4))

    def test_pause_epoch_and_expiry(self):
        capture = CrashCapture(SESSION)
        capture.accept(encode(sample()),0)
        self.assertIsNotNone(capture.latest(250_000_000))
        self.assertIsNone(capture.latest(250_000_001))
        capture.accept(encode(sample(sequence=2,native_tick=2,paused=True)),250_000_002)
        self.assertIsNone(capture.latest(250_000_002))
        self.assertIsNone(capture.accept(encode(sample(sequence=3,native_tick=3)),250_000_003))
        self.assertIsNotNone(capture.accept(encode(sample(sequence=4,native_tick=4,frame=frame(epoch=2))),250_000_004))
        with self.assertRaises(ValueError): capture.latest(0)

    def test_malformed_fields(self):
        packet = encode(sample())
        for bad in (b'',packet[:-1],packet+b'x',b'URL!'+packet[4:],packet[:7]+b'\x02'+packet[8:],
                    packet[:8]+bytes(16)+packet[24:],encode(sample(frame=b'x'*16)),
                    encode(sample(frame=frame(epoch=0))), encode(sample(frame=frame(reserved=1)))):
            with self.subTest(bad=bad), self.assertRaises(ValueError): CrashCapture(SESSION).accept(bad,1)
        for session in (bytes(16), b'x', 'x'*16):
            with self.assertRaises(ValueError): CrashCapture(session)
        with self.assertRaises(ValueError): encode(sample(position=(0,0,2147483648)))
        with self.assertRaises(ValueError): encode(sample(rotation=(0,0,float('nan'))))

    def test_source_has_no_memory_or_input_writes(self):
        root = Path(__file__).resolve().parents[1]
        source = (root/'integration/crash_pose/CrashPoseMod.cs').read_text()
        self.assertNotRegex(source, r'\b(?:m|memory|ram|e\.Memory)\.Write')
        self.assertNotIn('e.Buttons =',source)
        self.assertNotIn('e.Memory.Read',source)
        self.assertIn('ReadOnlySpan<byte> ram = m.Ram',source)
        self.assertNotIn('PresentFrame(',source)

    def test_missing_adapter_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp, patch('tools.collect_crash_pose.private_root', return_value=Path(tmp)), \
                patch('tools.collect_crash_pose.subprocess.Popen') as popen:
            with self.assertRaises(FileNotFoundError): checked_launcher()
            popen.assert_not_called()

    def test_invalid_limits_fail_before_launch(self):
        for seconds,count in ((0,1),(301,1),(1,3001),(True,1)):
            with patch('tools.collect_crash_pose.subprocess.Popen') as popen:
                with self.assertRaises(ValueError): collect('unused.cue',seconds,count)
                popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
