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

## 2026-10-10 Cloud continuation: source/result consistency

Continue from actual remote PR #27 head 555ff79, branch
`feat/goal19-query-integrity`, not the historical M3.3 handoff. A bounded
read-only review requested with explicit `gpt-6-astra` override found a concrete
producer/consumer mismatch: an empty result was accepted with recorded roots=3,
and native oracle mode 2 imported root-19 output into unchanged root-3 sources.
The tool accepted that override; separate resolved-model attestation is not
exposed by this environment. No original Windows run was performed here.

`DecodeNeighbor` now checks empty roots have no leaves, and ordinary odd roots
have exactly one level-zero leaf with the source root identity and the original
signed `relative >> 4` coordinates. Ambiguous descriptor-zero/13-bit encodings
fail closed. Internal-root traversal membership is **not** certified. Existing
sentinel, owner/thread/epoch, source digest, count/bounds and all four false
receipt capabilities are unchanged. No native engine or guest memory writes.

The C-to-C# oracle now aligns source fixtures explicitly for roots 3/0/19,
accepts all three matching cases, and rejects all six mismatched cases with
ROOT_RESULT. Fourth authored native case tests negative relative X and
non-multiple-of-16 bound coordinates; source output and decoder agree. The
formerly false empty fixture now uses genuine recorded root 0; its root-3
variant is a required rejection, not a disabled test.

Cloud Linux: **180 tests, 179 PASS / 1 Windows guest32 ABI skip** with pinned
sm64ex/c1 and public Crash host sources, configured native C-to-.NET cross-check.
Native QueryTests **63 assertions PASS**; NativeQueryCompile against public
RecompOne.Runtime source build **0 errors / 0 warnings**, .NET 10.0.401.
All are **VERIFIED_SYNTHETIC**. Both hosted source-only CI workflows cover this
branch; Linux additionally builds the C# oracle so cross-checks are not skipped.

This hardening does **not** explain, repair or relax the original Windows
QUERY_SENTINEL. The unobserved private trailer witness still requires a fresh
sealed, explicitly authorized local Windows in-level test. G1-G6 remain blocked;
no surfaces, material mapping, frame/lifetime proof or playable fusion is claimed.
