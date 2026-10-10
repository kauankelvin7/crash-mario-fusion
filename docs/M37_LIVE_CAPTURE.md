# M3.7 — same-receiver real-game capture gate

**Status (2026-10-09):** local, bounded paired experiment performed; **paired receiver capture succeeded after the epoch fix: 1,187 Crash + 1,017 Mario packets, zero rejects/holes, private audit CONSISTENT**. No native physics mutation, shared geometry, calibration, or release.

## Original-runtime attempt (pre-fix)

On the authorized Windows PC, started the existing strict paired CMW1 receiver (one localhost UDP port, one monotonic receiver clock, 180 s) plus the verified dedicated Crash observer and Mario instrumented native executable in two responsive original-game windows. Existing strict bindings were Crash level 9 / epoch 1 and Mario level 6 / area 1 / epoch 1. The private receiver's final summary reported **2,116 UDP attempts, Crash 1 accepted, Mario 0 accepted, 2,115 FRAME_GENERATION_MISMATCH**. Session mismatch, malformed and replay counts were all zero. The experiment demonstrated real game-origin datagram receipt but **did not validate paired timing or cross-engine comparability**. Both games were closed afterward. Retain raw logs and game data privately.

## Source-only corrective increment

The pre-existing receiver required a static observer epoch. The new **explicit opt-in** `-AllowNativeEpochRebind` switch on `tools/windows/Start-PairedObservation.ps1` enables `tools.native_epoch_observer.NativeEpochObserver`. This continues to use the original two-slot, finite, localhost, monotonic-clock receiver. Only packets with the correct engine-specific private session, supported phase, newer sequence number, unpaused flag, **known original-game level/area** (Crash: level 9; Mario: level 6 or 16, area 1) and newer observer epoch may authorize a rebinding. Source-chosen unknown levels, wrong sessions, stale generations and sequence replays are rejected. The first authorized descriptor may establish the initial engine-local identity. This policy does **not authenticate the engine process**, establish source timestamps, certify Crash postphysics or eliminate all semantic scene discontinuities; it is a narrowly scoped observer test.

From PowerShell 7 at repository root (one receiver process, 30–300 s), after checking fresh private original game builds:

```powershell
./tools/windows/Start-PairedObservation.ps1 -CrashLevel 9 -MarioLevel 6 -MarioArea 1 -CrashEpoch 1 -MarioEpoch 1 -MaxAgeNs 500000000 -MaxGapNs 2000000000 -Seconds 180 -MaxPackets 7000 -Port 39100 -AllowNativeEpochRebind
```

This command **only starts the receiver** and writes a private configuration with independent per-engine sessions. The two original-game emitters must be launched separately with session/port values from the private local config, as during the initial original-runtime attempt. Do not post tokens, raw poses, configs, executable/game files or disc paths. Have the operator enter a playable level and move/jump in both windows during the same bounded interval. Then audit the new private paired folder with `tools.audit_paired_capture` and inspect both accepted source counters. Any zero-source count is failure of the **paired** gate, even if standalone captures passed.

## Verification and remaining gates

- New native epoch policy and its deterministic tests passed with the full **94/94 local Windows source/native-oracle suite**; no game was launched by this suite.
- **Corrected real original-runtime paired receiver capture: VERIFIED_REAL receiver-only**; 2,204 accepted packets under one receiver clock and 1,108 comparable status rows. No physical synchronization verified.
- Physical synchronization, Crash native postphysics frame ownership, unique fixed-point position interpretation, shared landmarks and actual collision-world ownership remain **BLOCKED**.
- No release, no main merge, no commercial game files sent to GitHub.
