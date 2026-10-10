"""Bounded, session-scoped observer-epoch rebind for authorized native captures.

Only explicitly allowed levels/areas may acquire a new local receiver binding.
Neither frame identity nor the original-game source clock is authenticated by
a raw UDP packet: this policy requires a private per-session token and loopback.
"""
from integration.observation_alignment import Binding, descriptor
from integration.world_snapshot import CRASH, MARIO, UNKNOWN_DIAGNOSTIC, POST_MARIO_UPDATE, decode
from tools.collect_observations import PairedObserver


class NativeEpochObserver(PairedObserver):
    def __init__(self, bindings, allowed, *, clock_id, max_age_ns, max_gap_ns):
        super().__init__(bindings, clock_id=clock_id, max_age_ns=max_age_ns,
                         max_gap_ns=max_gap_ns)
        if set(allowed) != {CRASH, MARIO}:
            raise ValueError("Explicit allowlists required for both engines")
        self.allowed = {e: frozenset(allowed[e]) for e in allowed}
        if any(not options for options in self.allowed.values()):
            raise ValueError("Empty native level/area allowlist")

    def accept(self, packet, now_ns, *, peer="127.0.0.1"):
        if peer == "127.0.0.1":
            try:
                value = decode(packet)
                engine = value.engine
                bound = self.alignment.bindings[engine]
                identity = descriptor(engine, value.frame)
                prior = descriptor(engine, bound.frame)
                location = identity.level if engine == CRASH else (identity.level, identity.area)
                phase = UNKNOWN_DIAGNOSTIC if engine == CRASH else POST_MARIO_UPDATE
                if (location in self.allowed[engine] and value.session == bound.session
                        and value.phase == phase and not value.paused
                        and value.sequence > self.alignment.sequences[engine]
                        and value.frame != bound.frame):
                    if not self.sources[engine]["accepted"] and not self.alignment.sequences[engine]:
                        self.alignment.bindings[engine] = Binding(bound.session, value.frame)
                        self.alignment.store.frames[engine] = value.frame
                    elif identity.observer_epoch > prior.observer_epoch:
                        self.rebind(engine, Binding(bound.session, value.frame))
            except (ValueError, TypeError):
                pass
        return super().accept(packet, now_ns, peer=peer)
