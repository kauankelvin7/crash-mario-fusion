# GOAL #19: original source-query sentinel investigation

**2026-10-10, experimental, NOT PLAYABLE.** This checkpoint does not make native Crash colliders usable and does not merge to main.

## New genuine Windows evidence

In a fresh original Crash Bandicoot Windows session, the authorised PID/HWND-scoped `operator_harness.py` successfully found and focused the private original game's own window and sent Enter, Z, Z and an Up movement command, bounded and with verified foreground ownership. The original `ZoneQueryOctrees` diagnostic hook **was invoked**; unlike previous non-interactive startup probes it generated **one source-level rejection: `InvalidDataException:QUERY_SENTINEL`**, rather than zero activity. No successful query receipt, verified floor/physics contact, shared-world Mario movement, camera projection, scene object interaction or final playable build was observed. The original game PID was automatically stopped after the 65-second bounded session; no original game remains running. Runtime logs and retail data remain private under the user's `LOCALAPPDATA`.

## Narrow source-only change

Added opt-in `TRAILER_DIAGNOSTIC` message for an otherwise rejected `QUERY_SENTINEL` result, bounded by the existing eight-rejection budget. The witness reports only the returned count and three 32-bit trailer/previous words. It validates memory owner, original thread, observation epoch, PS1 RAM span and count; it does **not** serialize RAM, change parser acceptance, repair malformed results, disable sentinels, assign materials, create colliders, feed libsm64, or alter original-game memory. Retains `SurfacesAllowed=false`.

Compiled on the user's isolated native Windows .NET SDK 10.0.401: **zero errors/warnings**. Native C# query fixture: **53 checks passed** including owner/thread/epoch rejection and bounded trailer observation. **The new log message has not yet been observed in an original-game run.** It must be retested only from a new, independently sealed private probe build, preserving original host binary hashes and previous private evidence.

## Missing acceptance

1. Record an original level query with a successful source-owned sentinel, coherent scene/neighbor epochs, native allocation ownership and material mapping. Do not erase the rejection or assume an authored floor.
2. Match original Crash GTE same-frame projection and full visible-depth source to original libsm64 Mario mesh.
3. Validate real, independently controllable Mario with authentic Crash collisions and one shared physical object, then native Windows reliability and performance.

Source-only tests and successful loading of a diagnostic hook do not certify game playability. Keep the parent [GOAL #19](https://github.com/kauankelvin7/crash-mario-fusion/issues/19) open and any PR in draft.
