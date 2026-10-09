"""VERIFIED_SYNTHETIC: production C emitter/localhost, native source compilation.

No retail data, game execution, or calibration; deterministic clock only in fixture.
"""
from dataclasses import replace
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import unittest

from integration.world_snapshot import Snapshot, MARIO, POST_MARIO_UPDATE, decode, encode
from tools.collect_pose import MarioCapture, frame_descriptor, require_valid_capture
from tools.prepare_integration import prepare, PIN

ROOT = Path(__file__).resolve().parents[1]
SESSION = bytes.fromhex('00112233445566778899aabbccddeeff')


def sample(**changes):
    return replace(Snapshot(MARIO, POST_MARIO_UPDATE, SESSION,
                            struct.pack('!4shhII', b'M31A', 9, 1, 0, 1),
                            1, 42, (1.25, 2.5, -3.75), (-32768, 0, 32767), 3, 8), **changes)


class CaptureTests(unittest.TestCase):
    def test_session_sequence_and_frame_transitions(self):
        store = MarioCapture(SESSION)
        self.assertIsNotNone(store.accept(encode(sample()), 100))
        self.assertIsNone(store.accept(encode(sample()), 101))
        self.assertIsNone(store.accept(encode(sample(session=b'x'*16, sequence=2)), 102))
        frame2 = struct.pack('!4shhII', b'M31A', 9, 2, 0, 2)
        row = store.accept(encode(sample(sequence=3, frame=frame2)), 103)
        self.assertEqual(row['native_area'], 2)
        self.assertEqual(row['native_frame_generation'], 'unknown')
        self.assertFalse(row['calibration_ready'])
        self.assertIsNone(store.accept(encode(sample(sequence=4)), 104))
        conflict = struct.pack('!4shhII', b'M31A', 9, 3, 0, 2)
        self.assertIsNone(store.accept(encode(sample(sequence=4, frame=conflict)), 105))

    def test_pause_unavailable_and_receiver_age(self):
        store = MarioCapture(SESSION)
        self.assertIsNone(store.latest(0))
        store.accept(encode(sample()), 1)
        self.assertIsNotNone(store.latest(250_000_001))
        self.assertIsNone(store.latest(250_000_002))
        store.accept(encode(sample(sequence=2, paused=True)), 250_000_003)
        self.assertIsNone(store.latest(250_000_003))
        with self.assertRaises(ValueError): store.latest(2)
        with self.assertRaises(ValueError): store.accept(encode(sample()), 2)

    def test_malformed_nonfinite_and_unknown_identity(self):
        store = MarioCapture(SESSION)
        packet = encode(sample())
        for bad in (b'', packet[:-1], packet+b'x', packet[:48]+struct.pack('!f', float('nan'))+packet[52:],
                    encode(sample(frame=b'x'*16))):
            with self.subTest(packet=bad), self.assertRaises(ValueError): store.accept(bad, 1)
        with self.assertRaises(ValueError): MarioCapture(bytes(16))


    def test_empty_capture_fails_closed_without_erasing_summary(self):
        # A successful game process exit is not equivalent to observing CMW1.
        for count in (0, -1, None, False, True):
            with self.subTest(count=count), self.assertRaises(RuntimeError):
                require_valid_capture(count)
        self.assertIsNone(require_valid_capture(1))


class NativePoseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = shutil.which('gcc')
        if cls.cc is None:
            raise unittest.SkipTest('GCC required for production C observer')
        cls.temp = tempfile.TemporaryDirectory(prefix='cm64-pose-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.exe = Path(cls.temp.name)/('pose.exe' if os.name == 'nt' else 'pose')
        command = [cls.cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-DCM64_POSE_TEST_CLOCK',
                   '-I'+str(ROOT/'integration/sm64'), str(ROOT/'integration/sm64/cm64_pose.c'),
                   str(ROOT/'tests/integration/native_pose.c'), '-o', str(cls.exe)]
        if os.name == 'nt': command += ['-lws2_32']
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=45)
        # Also compile the actual monotonic clock branch, not only the test clock.
        command = [x for x in command if x != '-DCM64_POSE_TEST_CLOCK']
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=45)
        command.insert(1, '-DCM64_POSE_TEST_CLOCK')
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=45)

    def run_sender(self, commands, **overrides):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(('127.0.0.1', 0))
            receiver.settimeout(.1)
            env = os.environ.copy()
            env.update(CM64_POSE_ENABLE='1', CM64_POSE_SESSION=SESSION.hex(),
                       CM64_POSE_PORT=str(receiver.getsockname()[1]))
            env.update(overrides)
            result = subprocess.run([str(self.exe)], input=commands, env=env,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout+result.stderr, '')  # no per-sample console spam
            packets = []
            while True:
                try:
                    packet, peer = receiver.recvfrom(256)
                except socket.timeout:
                    break
                self.assertEqual(peer[0], '127.0.0.1')
                packets.append(decode(packet))
            return packets

    def test_wire_rate_and_engine_local_tick_wrap(self):
        rows = self.run_sender('0 4294967295 9 1 v\n0 9 9 1 v\n99 9 9 1 v\n100 0 9 1 v\n')
        self.assertEqual(len(rows), 2)
        self.assertEqual([x.sequence for x in rows], [1, 2])
        self.assertEqual([x.native_tick for x in rows], [2**32-1, 0])
        self.assertEqual(rows[0].position, (1.25, 2.5, -3.75))
        self.assertEqual(rows[0].rotation, (-32768, 0, 32767))
        self.assertEqual((rows[0].state, rows[0].state_flags), (0x12345678, 0x80000001))
        self.assertEqual(frame_descriptor(rows[0].frame), (9, 1, 1))

    def test_invalid_nan_pause_lifecycle_and_area(self):
        rows = self.run_sender('0 0 9 1 v\n100 1 9 1 n\n200 2 9 1 v\n'
                               '300 3 9 1 i\n400 4 9 1 v\n500 5 9 2 v\n'
                               '600 6 0 0 v\n700 7 9 2 v\n')
        self.assertEqual([frame_descriptor(x.frame) for x in rows],
                         [(9,1,1),(9,1,2),(9,1,3),(9,2,4),(9,2,5)])
        self.assertEqual([x.sequence for x in rows], list(range(1,6)))

    def test_disabled_and_malformed_configuration(self):
        for overrides in ({'CM64_POSE_ENABLE':'0'}, {'CM64_POSE_ENABLE':''},
                          {'CM64_POSE_SESSION':'0'*32}, {'CM64_POSE_SESSION':'z'*32},
                          {'CM64_POSE_PORT':' 1234'}, {'CM64_POSE_PORT':'99999'}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.run_sender('0 0 9 1 v\n', **overrides), [])

    def test_time_bound_and_no_catchup_burst(self):
        rows = self.run_sender('0 0 9 1 v\n5000 1 9 1 v\n5000 2 9 1 v\n300000 3 9 1 v\n')
        self.assertEqual([x.sequence for x in rows], [1,2])


class NativePoseHookTests(unittest.TestCase):
    def test_pinned_source_hooks_compile_and_preserve_local_edits(self):
        path = os.environ.get('CM64_SM64EX_ROOT') or os.environ.get('SM64EX_ROOT')
        if not path or not shutil.which('gcc'):
            self.skipTest('Set CM64_SM64EX_ROOT to clean pinned source and provide GCC')
        source = Path(path)
        with tempfile.TemporaryDirectory(prefix='cm64-pose-source-') as tmp:
            output = Path(tmp)/'source'
            prepare(source, output)
            before = (output/'src/game/level_update.c').read_bytes()
            prepare(source, output)
            self.assertEqual((output/'src/game/level_update.c').read_bytes(), before)
            for name in ('level_update', 'area', 'interaction'):
                result = subprocess.run(['gcc', '-c', '-DVERSION_US', '-D_LANGUAGE_C',
                    '-DNON_MATCHING', '-DAVOID_UB', '-fno-strict-aliasing', '-fwrapv',
                    '-Iinclude', '-Isrc', '-I.', f'src/game/{name}.c', '-o', str(Path(tmp)/(name+'.o'))],
                    cwd=output, capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            (output/'src/game/area.c').write_text('// user edit\n')
            with self.assertRaisesRegex(ValueError, 'Preserve local edits'):
                prepare(source, output)
