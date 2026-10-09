# M3.5 — private paired-receiver capture audit

This increment is **offline receiver-log self-consistency only**. It does not run either original game, prove source authenticity, establish shared coordinates or synchronize gameplay. It does not read commercial files, issue input, inject surfaces, or transmit telemetry.

## New read-only command

After an operator explicitly starts and completes the three-terminal paired receiver procedure in [WINDOWS.md](WINDOWS.md), locate the **private** `paired-...` folder below `%LOCALAPPDATA%/CrashMarioFusion/telemetry`. From the repository root, with native MSYS2 MinGW64 Python available:

```powershell
& 'C:/msys64/mingw64/bin/python.exe' -m tools.audit_paired_capture --capture '<private-paired-folder>'
```

The command reads **only** `observations.jsonl` and `summary.json` in that local folder. It bounds accepted file sizes/row counts, rejects symbolic-link input files, verifies one receiver clock and monotonic timestamps, verifies accepted engine sequences/holes/gaps, validates admission and rejection counters against the receiver summary, and rejects false claims of calibration, real-game validation or physical synchronization. It emits aggregate JSON only; never prints frame descriptors, sessions, paths, raw XYZ poses, timestamps, or private input files. Nonzero exit = failure or inconsistent log, not proof of a game bug. `EMPTY_CAPTURE` is not gameplay evidence.

Evidence classification for this tool: **VERIFIED_SYNTHETIC** when its unit tests pass, or **RECEIVER_LOG_SELF_CONSISTENCY_ONLY** when it accepts a locally supplied original receiver capture. The tool cannot authenticate whether a UDP sender was an original game, measure one-way source latency, certify Crash postphysics callback ownership, guarantee simultaneous native frame generations or support/calibrate native collision. Even `paired_telemetry_status_records > 0` does **not** clear those gates. All output explicitly maintains `physical_status=BLOCKED` and `calibration_ready=false`.

## Next real game gate

1. On the user's authorized Windows PC, finish source-only tests and the operator-led paired receiver experiment; use only lawfully owned, local files and **do not upload** games, logs, JSONL, receiver configs or game executables.
2. Run this audit against the locally completed capture. Keep the aggregate report private by default. Interpret zero accepted packets, pause/epoch invalidation, source gaps and summary mismatch as diagnostics, not automatic game failures.
3. Independently prove Crash postphysics-native update ownership and native generation/zone identity, establish real noncollinear corresponding landmarks with holdouts, inspect authentic source geometry/material provenance and live Mario pool occupancy/lifetime before any shared-world collision experiment.
4. Preserve native physics and inputs in both engines, original source pins and the pre-existing M2 real coin-to-jump evidence. Do not merge to `main` or publish a playable release.

**Scope:** M3.5 adds one pure Python audit module and deterministic tests. No native adapter, original engine, event-bus protocol, collector, pin or launcher is modified. For CI, source-only Linux/Windows PR triggers may include the stacked M3.4 base branch; those runs are still synthetic fixture checks.
