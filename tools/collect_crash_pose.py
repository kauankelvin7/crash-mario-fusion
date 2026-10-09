"""Operator-only finite Crash diagnostic capture. No calibration or remote paths."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time
import uuid

from integration.world_snapshot import CRASH, UNKNOWN_DIAGNOSTIC, decode
from tools.prepare_crash_pose import PIN, private_root


def frame_descriptor(frame):
    magic, level, epoch, reserved = struct.unpack('!4sIII', frame)
    if magic != b'M32D' or not epoch or reserved or level > 0xFFFF:
        raise ValueError('Unknown Crash diagnostic descriptor')
    return level, epoch


class CrashCapture:
    def __init__(self, session):
        if type(session) is not bytes or len(session) != 16 or not any(session):
            raise ValueError('Nonzero session required')
        self.session = session
        self.sequence = self.tick = self.epoch = 0
        self.frame = self.value = None
        self.clock_ns = self.received_ns = -1

    def accept(self, packet, now_ns):
        if type(now_ns) is not int or now_ns < 0 or now_ns < self.clock_ns:
            raise ValueError('Receiver clock must be monotonic')
        self.clock_ns = now_ns
        value = decode(packet)
        if (value.engine != CRASH or value.phase != UNKNOWN_DIAGNOSTIC or value.session != self.session or
                value.sequence <= self.sequence or value.native_tick <= self.tick):
            return None
        level, epoch = frame_descriptor(value.frame)
        if epoch < self.epoch or (epoch == self.epoch and value.frame != self.frame):
            return None
        # Paused frames are not produced. If received, invalidate and consume ordering;
        # resumption must use a new epoch, never resurrect the paused frame.
        if epoch == self.epoch and self.value is not None and self.value.paused and not value.paused:
            return None
        self.sequence, self.tick, self.epoch = value.sequence, value.native_tick, epoch
        self.frame, self.value, self.received_ns = value.frame, value, now_ns
        if value.paused:
            return None
        row = asdict(value)
        row.update(session=value.session.hex(), frame=value.frame.hex(), native_level=level,
                   observer_epoch=epoch, native_frame_generation='unknown', calibration_ready=False,
                   phase_name='UNKNOWN_DIAGNOSTIC', tick_kind='observer_pad_callback',
                   rotation_kind='signed_native_raw', receiver_monotonic_ns=now_ns)
        return row

    def latest(self, now_ns):
        if type(now_ns) is not int or now_ns < 0 or now_ns < self.clock_ns:
            raise ValueError('Receiver clock must be monotonic')
        self.clock_ns = now_ns
        if self.value is None or self.value.paused or now_ns-self.received_ns > 250_000_000:
            return None
        return self.value


def checked_launcher():
    root = private_root()
    app = root/'app'
    manifest = json.loads((root/'observer-build.json').read_text(encoding='utf-8'))
    files = ('CrashBandicoot.exe', 'CrashBandicoot.dll', 'RecompOne.Runtime.dll',
             'mods/cm64-crash-pose/CrashPoseMod.cs', 'mods/cm64-crash-pose/mod.json')
    if manifest['pin'] != PIN or set(manifest['hashes']) != set(files):
        raise ValueError('Unrecognized observer build')
    for name in files:  # Fixed local allowlist, never paths supplied by UDP or a manifest.
        if hashlib.sha256((app/name).read_bytes()).hexdigest() != manifest['hashes'][name]:
            raise ValueError('Observer build changed; rebuild in a fresh private directory')
    settings = json.loads((app/'settings.json').read_text(encoding='utf-8-sig'))
    if settings.get('ModsConfigured') is not True or settings.get('ActiveMods') != ['cm64-crash-pose']:
        raise ValueError('Diagnostic adapter must be the only active mod')
    return app/'CrashBandicoot.exe'


def collect(crash_disc, seconds=60, count=600):
    if os.name != 'nt' or type(seconds) is not int or type(count) is not int or not 1 <= seconds <= 300 or not 1 <= count <= 3000:
        raise ValueError('Native Windows capture requires 1..300 seconds / 1..3000 samples')
    exe = checked_launcher()  # Fails before launching if missing/inactive/modified.
    disc = Path(crash_disc).resolve(strict=True)
    if not disc.is_file() or disc.suffix.lower() not in ('.cue', '.chd'):
        raise ValueError('Supply your own local Crash CUE or CHD')
    root = (Path(os.environ['LOCALAPPDATA'])/'CrashMarioFusion/telemetry').resolve()
    repo = Path(__file__).resolve().parents[1]
    if root == repo or repo in root.parents:
        raise ValueError('Telemetry must remain outside Git')
    session = uuid.uuid4().bytes
    folder = root/('crash-'+uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    capture = CrashCapture(session)
    accepted = rejected = attempts = 0
    child = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, \
                (folder/'snapshots.jsonl').open('x', encoding='utf-8') as output, \
                (folder/'crash.log').open('x', encoding='utf-8') as game_log:
            receiver.bind(('127.0.0.1', 0))
            receiver.settimeout(.05)
            environment = {k: v for k, v in os.environ.items() if not k.upper().startswith('CM64_')}
            environment.update(CM64_CRASH_POSE_ENABLE='1', CM64_CRASH_POSE_SESSION=session.hex(),
                               CM64_CRASH_POSE_PORT=str(receiver.getsockname()[1]))
            deadline = time.monotonic()+seconds
            print(f'Private capture: {folder}; {seconds}s/{count} samples maximum; Ctrl+C stops Crash.', flush=True)
            try:
                child = subprocess.Popen([str(exe), '--run', str(disc)], cwd=exe.parent,
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
                            attempts += 1; rejected += 1
                            continue
                        raise
                    attempts += 1
                    try:
                        row = capture.accept(packet, time.monotonic_ns()) if peer[0] == '127.0.0.1' else None
                    except ValueError:
                        row = None
                    if row is None:
                        rejected += 1
                    else:
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
                        child.kill(); child.wait(timeout=5)
    finally:
        summary = dict(accepted=accepted, rejected=rejected, attempts=attempts,
                       calibration_ready=False, live_gameplay_verified=False,
                       phase='UNKNOWN_DIAGNOSTIC', native_frame_generation='unknown',
                       freshness='receiver arrival only; source delay unknown')
        (folder/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    if not accepted:
        raise RuntimeError(f'No valid diagnostic pose; adapter/runtime not validated. See {folder}')
    print(f'{accepted} diagnostic samples; NOT_CALIBRATION_READY. Logs: {folder}')
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crash-disc', required=True)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--count', type=int, default=600)
    args = parser.parse_args()
    collect(args.crash_disc, args.seconds, args.count)
