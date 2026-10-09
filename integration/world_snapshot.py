"""CMW1 read-only native pose wire contract; no physics or pose mutation.

Mario phase 1 has a native post-update emitter. Crash phase 0 is diagnostic
controller-poll sampling, NOT proven after physics, and its tick is a callback
ordinal. Frames are observer-local; no shared spatial or temporal calibration.
"""
from dataclasses import dataclass
import math
import struct

CRASH, MARIO = 1, 2
UNKNOWN_DIAGNOSTIC = 0
POST_MARIO_UPDATE, POST_CRASH_PHYSICS, PRE_CRASH_GPU = 1, 2, 3
HEADER = struct.Struct("!4sBBH16s16sII")
PAYLOAD = {CRASH: struct.Struct("!3i3iII"), MARIO: struct.Struct("!3f3hII")}


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 2**bits:
        raise ValueError(f"Expected uint{bits}")


@dataclass(frozen=True)
class Snapshot:
    engine: int
    phase: int
    session: bytes
    frame: bytes
    sequence: int
    native_tick: int
    position: tuple
    rotation: tuple
    state: int
    state_flags: int
    paused: bool = False


def encode(snapshot):
    if type(snapshot.engine) is not int or snapshot.engine not in PAYLOAD:
        raise ValueError("Unknown engine")
    allowed = (POST_MARIO_UPDATE,) if snapshot.engine == MARIO else (UNKNOWN_DIAGNOSTIC, POST_CRASH_PHYSICS, PRE_CRASH_GPU)
    if type(snapshot.phase) is not int or snapshot.phase not in allowed:
        raise ValueError("Phase incompatible with native engine")
    for identity in (snapshot.session, snapshot.frame):
        if type(identity) is not bytes or len(identity) != 16 or not any(identity):
            raise ValueError("Nonzero 16-byte session/frame identity required")
    for number in (snapshot.sequence,snapshot.native_tick,snapshot.state,snapshot.state_flags):
        _uint(number,32)
    if snapshot.sequence == 0 or type(snapshot.paused) is not bool:
        raise ValueError("Nonzero sequence and boolean paused required")
    if len(snapshot.position) != 3 or len(snapshot.rotation) != 3:
        raise ValueError("Three native position and rotation values required")
    if snapshot.engine == CRASH:
        values = snapshot.position + snapshot.rotation
        if any(type(n) is not int or not -(2**31) <= n < 2**31 for n in values):
            raise ValueError("Crash position/rotation must remain signed native int32")
    else:
        if any(isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n)
               for n in snapshot.position):
            raise ValueError("Mario position must be finite native float32")
        if any(type(n) is not int or not -32768 <= n <= 32767 for n in snapshot.rotation):
            raise ValueError("Mario faceAngle must remain signed native int16")
    try:
        return (HEADER.pack(b"CMW1",snapshot.engine,snapshot.phase,int(snapshot.paused),
                            snapshot.session,snapshot.frame,snapshot.sequence,snapshot.native_tick)
                + PAYLOAD[snapshot.engine].pack(*snapshot.position,*snapshot.rotation,
                                               snapshot.state,snapshot.state_flags))
    except (OverflowError,struct.error) as exc:
        raise ValueError("Snapshot cannot be represented in its native wire types") from exc


def decode(packet):
    if type(packet) is not bytes or len(packet) < HEADER.size:
        raise ValueError("Truncated packet")
    magic,engine,phase,flags,session,frame,seq,tick = HEADER.unpack_from(packet)
    if magic != b"CMW1" or engine not in PAYLOAD or flags not in (0,1):
        raise ValueError("Unsupported magic/engine/flags")
    if len(packet) != HEADER.size + PAYLOAD[engine].size:
        raise ValueError("Incorrect native packet size")
    values = PAYLOAD[engine].unpack_from(packet,HEADER.size)
    snapshot=Snapshot(engine,phase,session,frame,seq,tick,values[:3],values[3:6],
                      values[6],values[7],bool(flags))
    encode(snapshot)  # one validation policy for outbound and untrusted inbound
    return snapshot


class SnapshotStore:
    """Two bounded observation slots; no queue, replay or extrapolated movement.

    Constructor binds reviewed engine frame identities. Level/zone/object
    generation changes require a new store; addresses are never identities.
    Freshness uses receiver-local time, never a cross-machine clock subtraction.
    """
    def __init__(self, session, frames, max_age_ns):
        sessions = dict(session) if type(session) is dict else {CRASH:session,MARIO:session}
        if set(sessions)!={CRASH,MARIO} or any(type(s) is not bytes or len(s)!=16 or not any(s)
                                              for s in sessions.values()):
            raise ValueError("Explicit session required for each engine")
        if set(frames) != {CRASH,MARIO} or any(type(f) is not bytes or len(f)!=16 or not any(f)
                                              for f in frames.values()):
            raise ValueError("Bind both native frame generations explicitly")
        if type(max_age_ns) is not int or not 0 < max_age_ns <= 10**9:
            raise ValueError("Receiver age bound must be 1..1000000000 ns")
        self.session,self.frames,self.max_age_ns = session,dict(frames),max_age_ns
        self.sessions = sessions
        self.slots = {}
        self.last_receive_ns = -1

    def accept(self, packet, receive_ns):
        _uint(receive_ns,64)
        if receive_ns < self.last_receive_ns:
            raise ValueError("Receiver monotonic clock moved backwards")
        snapshot=decode(packet)
        if snapshot.session != self.sessions[snapshot.engine] or snapshot.frame != self.frames[snapshot.engine]:
            return False
        previous=self.slots.get(snapshot.engine)
        if previous and snapshot.sequence <= previous[0].sequence:
            return False
        self.slots[snapshot.engine]=(snapshot,receive_ns)
        self.last_receive_ns=receive_ns
        return True

    def latest(self, engine, now_ns):
        _uint(now_ns,64)
        if now_ns < self.last_receive_ns:
            raise ValueError("Receiver monotonic clock moved backwards")
        value=self.slots.get(engine)
        if value is None or value[0].paused or now_ns-value[1] > self.max_age_ns:
            return None
        return value[0]
