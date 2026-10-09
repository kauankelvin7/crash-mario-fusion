"""Finite, localhost-only Mario CMW1 capture. Explicit operator launch, no calibration.

Logs stay in LOCALAPPDATA/CrashMarioFusion/telemetry, never a packet-selected path.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time
import uuid

from integration.world_snapshot import MARIO, decode


def frame_descriptor(frame):
    magic, level, area, reserved, generation = struct.unpack('!4shhII', frame)
    if magic != b'M31A' or level <= 0 or area <= 0 or reserved or not generation:
        raise ValueError('Unknown Mario observer frame descriptor')
    return level, area, generation


class MarioCapture:
    """One slot. Observer epoch changes invalidate prior correspondence, never calibrate."""
    def __init__(self, session):
        if type(session) is not bytes or len(session) != 16 or not any(session):
            raise ValueError('Fresh nonzero session required')
        self.session = session
        self.sequence = self.generation = 0
        self.frame = self.value = None
        self.received_ns = self.clock_ns = -1

    def accept(self, packet, now_ns):
        if type(now_ns) is not int or now_ns < 0 or now_ns < self.clock_ns:
            raise ValueError('Receiver clock must be monotonic')
        self.clock_ns = now_ns
        value = decode(packet)
        if value.engine != MARIO or value.session != self.session or value.sequence <= self.sequence:
            return None
        level, area, generation = frame_descriptor(value.frame)
        if generation < self.generation or (generation == self.generation and value.frame != self.frame):
            return None
        self.sequence, self.generation, self.frame = value.sequence, generation, value.frame
        self.value, self.received_ns = value, now_ns
        row = asdict(value)
        row.update(session=value.session.hex(), frame=value.frame.hex(),
                   native_level=level, native_area=area, observer_generation=generation,
                   native_frame_generation='unknown', calibration_ready=False,
                   receiver_monotonic_ns=now_ns)
        return row

    def latest(self, now_ns):
        if type(now_ns) is not int or now_ns < self.clock_ns:
            raise ValueError('Receiver clock must be monotonic')
        self.clock_ns = now_ns
        if self.value is None or self.value.paused or now_ns-self.received_ns > 250_000_000:
            return None
        return self.value


def require_valid_capture(accepted):
    """A successful process launch is not a verified native pose capture."""
    if type(accepted) is not int or accepted <= 0:
        raise RuntimeError('No valid Mario CMW1 pose; original gameplay observation NOT_VERIFIED. Consult private capture logs.')


def collect(mario_exe, seconds=60, count=600):
    if os.name != 'nt':
        raise ValueError('This operator workflow requires native Windows')
    if not 1 <= seconds <= 300 or not 1 <= count <= 3000:
        raise ValueError('Bound capture to 1..300 seconds and 1..3000 accepted packets')
    mario_exe = Path(mario_exe).resolve(strict=True)
    if not mario_exe.is_file() or mario_exe.suffix.lower() != '.exe':
        raise ValueError('Supply the instrumented local Mario executable')
    root = (Path(os.environ['LOCALAPPDATA'])/'CrashMarioFusion'/'telemetry').resolve()
    repo = Path(__file__).resolve().parents[1]
    if root == repo or repo in root.parents:
        raise ValueError('Private telemetry must remain outside the repository')
    session = uuid.uuid4().bytes
    folder = root/uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    capture = MarioCapture(session)
    accepted = rejected = attempts = 0
    child = None
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, \
            (folder/'snapshots.jsonl').open('x', encoding='utf-8') as output, \
            (folder/'mario.log').open('x', encoding='utf-8') as game_log:
        receiver.bind(('127.0.0.1', 0))
        receiver.settimeout(.05)
        environment = os.environ.copy()
        for key in ('CM64_SESSION', 'CM64_PORT', 'CM64_APPLY', 'CM64_KEYBOARD_ARM'):
            environment.pop(key, None)
        environment.update(CM64_POSE_ENABLE='1', CM64_POSE_SESSION=session.hex(),
                           CM64_POSE_PORT=str(receiver.getsockname()[1]))
        deadline = time.monotonic()+seconds
        print(f'Private capture: {folder}; stop with Ctrl+C; maximum {seconds}s/{count} samples.', flush=True)
        try:
            child = subprocess.Popen([str(mario_exe)], cwd=mario_exe.parent,
                                     env=environment, stdout=game_log, stderr=subprocess.STDOUT)
            while time.monotonic() < deadline and accepted < count and attempts < 10000:
                if child.poll() is not None:
                    break
                try:
                    packet, peer = receiver.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError as exc:
                    if getattr(exc, 'winerror', None) == 10040:
                        attempts += 1
                        rejected += 1
                        continue
                    raise
                attempts += 1
                try:
                    row = capture.accept(packet, time.monotonic_ns()) if peer[0] == '127.0.0.1' else None
                except ValueError:
                    row = None
                if row is None:
                    rejected += 1
                    continue
                output.write(json.dumps(row, allow_nan=False)+'\n')
                accepted += 1
        except KeyboardInterrupt:
            pass
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
    summary = dict(accepted=accepted, rejected=rejected, attempts=attempts,
                   live_gameplay_verified=False, calibration_ready=False,
                   crash_continuous_emitter='pending',
                   freshness='receiver arrival only; source delay unknown')
    (folder/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    require_valid_capture(accepted)
    print(f'Capture complete: {accepted} accepted, {rejected} rejected. Calibration remains gated.')
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mario-exe', required=True)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--count', type=int, default=600)
    args = parser.parse_args()
    collect(args.mario_exe, args.seconds, args.count)
