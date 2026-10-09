"""Two-slot CMW1 observational correlation; never synchronizes game physics.

All arrival stamps must belong to the explicitly declared SAME receiver clock.
Independent collectors' monotonic origins cannot be compared automatically.
"""
from dataclasses import dataclass
from enum import Enum

from integration.world_snapshot import (CRASH,MARIO,UNKNOWN_DIAGNOSTIC,
    POST_MARIO_UPDATE,Snapshot,SnapshotStore,decode)
from tools.collect_crash_pose import frame_descriptor as crash_descriptor
from tools.collect_pose import frame_descriptor as mario_descriptor


class Reason(str,Enum):
    ACCEPTED="ACCEPTED"
    MALFORMED="MALFORMED"
    SESSION="SESSION_MISMATCH"
    FRAME="FRAME_GENERATION_MISMATCH"
    REPLAY="DUPLICATE_OR_OLD_SEQUENCE"
    PHASE="UNSUPPORTED_PHASE"
    PAUSED="PAUSED_REBIND_REQUIRED"
    GAP="GAP_REBIND_REQUIRED"
    TIMEOUT="TIMEOUT"
    MISSING="SOURCE_MISSING"
    CLOCK="RECEIVER_CLOCK_REGRESSION"
    DOMAIN="RECEIVER_CLOCK_DOMAIN_MISMATCH"


@dataclass(frozen=True)
class Binding:
    session: bytes
    frame: bytes


@dataclass(frozen=True)
class Descriptor:
    level: int
    area: int | None
    observer_epoch: int


def descriptor(engine,frame):
    if engine==CRASH:
        level,epoch=crash_descriptor(frame)
        return Descriptor(level,None,epoch)
    level,area,epoch=mario_descriptor(frame)
    return Descriptor(level,area,epoch)


@dataclass(frozen=True)
class Admission:
    accepted: bool
    reason: Reason


@dataclass(frozen=True)
class SourceView:
    engine: int
    reason: Reason
    identity: Descriptor
    age_ns: int | None
    snapshot: Snapshot | None


@dataclass(frozen=True)
class Comparison:
    sources: tuple
    telemetry_comparable: bool
    receiver_arrival_separation_ns: int | None
    physical_status: str = "BLOCKED"
    calibration_ready: bool = False
    gate: str = "Crash postphysics/native frame generation unverified; arrivals are not latency"


class ObservationAlignment:
    def __init__(self,bindings,*,receiver_clock_id,max_age_ns,max_gap_ns):
        if (not isinstance(receiver_clock_id,str) or not 1<=len(receiver_clock_id)<=128 or
                type(max_age_ns) is not int or not 0<max_age_ns<=10**9 or
                type(max_gap_ns) is not int or not max_age_ns<=max_gap_ns<=300_000_000_000):
            raise ValueError("Explicit bounded receiver clock/age/gap required")
        if set(bindings)!={CRASH,MARIO} or any(not isinstance(b,Binding) for b in bindings.values()):
            raise ValueError("Bind both independent sources explicitly")
        self.bindings=dict(bindings)
        for engine,binding in bindings.items(): descriptor(engine,binding.frame)
        self.store=SnapshotStore({e:b.session for e,b in bindings.items()},
                                 {e:b.frame for e,b in bindings.items()},max_age_ns)
        self.clock_id,self.clock_ns,self.max_gap_ns=receiver_clock_id,-1,max_gap_ns
        self.gates={e:None for e in bindings}
        self.sequences={e:0 for e in bindings}

    def _clock(self,now_ns,clock_id):
        if clock_id!=self.clock_id: return Reason.DOMAIN
        if type(now_ns) is not int or not 0<=now_ns<2**64: return Reason.MALFORMED
        if now_ns<self.clock_ns: return Reason.CLOCK
        self.clock_ns=now_ns
        return None

    def accept(self,packet,receive_ns,*,receiver_clock_id):
        clock_error=self._clock(receive_ns,receiver_clock_id)
        if clock_error: return Admission(False,clock_error)
        try:
            value=decode(packet)
            identity=descriptor(value.engine,value.frame)
        except (ValueError,TypeError): return Admission(False,Reason.MALFORMED)
        engine=value.engine
        binding=self.bindings[engine]
        if value.session!=binding.session: return Admission(False,Reason.SESSION)
        if value.sequence<=self.sequences[engine]: return Admission(False,Reason.REPLAY)
        if value.phase!=(UNKNOWN_DIAGNOSTIC if engine==CRASH else POST_MARIO_UPDATE):
            return Admission(False,Reason.PHASE)
        if value.frame!=binding.frame:
            expected=descriptor(engine,binding.frame)
            if identity.observer_epoch>=expected.observer_epoch: self.gates[engine]=Reason.FRAME
            return Admission(False,Reason.FRAME)
        if self.gates[engine]: return Admission(False,self.gates[engine])
        previous=self.store.slots.get(engine)
        if previous and receive_ns-previous[1]>self.max_gap_ns:
            self.gates[engine]=Reason.GAP
            return Admission(False,Reason.GAP)
        if not self.store.accept(packet,receive_ns): return Admission(False,Reason.REPLAY)
        self.sequences[engine]=value.sequence
        if value.paused:
            self.gates[engine]=Reason.PAUSED
            return Admission(True,Reason.PAUSED) # Consume sequence, invalidate usability.
        return Admission(True,Reason.ACCEPTED)

    def rebind(self,engine,binding):
        if engine not in self.bindings or not isinstance(binding,Binding):
            raise ValueError("Explicit source binding required")
        identity=descriptor(engine,binding.frame)
        old=self.bindings[engine]
        if type(binding.session) is not bytes or len(binding.session)!=16 or not any(binding.session):
            raise ValueError("Nonzero capture session required")
        if binding.session==old.session:
            if identity.observer_epoch<=descriptor(engine,old.frame).observer_epoch:
                raise ValueError("Same-session rebind requires a newer explicit observer epoch")
        else: self.sequences[engine]=0
        self.bindings[engine]=binding
        self.store.sessions[engine]=binding.session
        self.store.frames[engine]=binding.frame
        self.store.slots.pop(engine,None)
        self.gates[engine]=None

    def evaluate(self,now_ns,*,receiver_clock_id):
        clock_error=self._clock(now_ns,receiver_clock_id)
        views=[]
        for engine in (CRASH,MARIO):
            previous=self.store.slots.get(engine)
            age=now_ns-previous[1] if previous and not clock_error else None
            reason=clock_error or self.gates[engine]
            if not reason:
                reason=Reason.MISSING if previous is None else Reason.TIMEOUT if age>self.store.max_age_ns else Reason.ACCEPTED
            value=self.store.latest(engine,now_ns) if reason==Reason.ACCEPTED else None
            views.append(SourceView(engine,reason,descriptor(engine,self.bindings[engine].frame),age,value))
        comparable=all(v.reason==Reason.ACCEPTED for v in views)
        separation=abs(self.store.slots[CRASH][1]-self.store.slots[MARIO][1]) if comparable else None
        return Comparison(tuple(views),comparable,separation)
