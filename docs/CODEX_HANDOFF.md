# Codex continuation handoff — after native Mario-to-Crash jump (2026-10-09)

> **Canonical task packet for the next Codex run on `m0-recon`.** Read `AGENTS.md`,
> `docs/STATUS.md`, `docs/EVIDENCE.md`, `docs/CONTRACT.md`, `docs/DECISIONS.md`
> and `docs/WINDOWS.md` before editing. Continue the existing project, not a new implementation.

**M3 increment (2026-10-09):** `feat/m3-coordinate-contract` adds read-only XYZ
observation and `tools/world_coordinates.py`, with explicit calibration,
float32 inverse-error guard and native floor bounds. Cloud checks: 17 Python,
27 compiled native-adapter fixtures, 9 PowerShell ASTs pass. These are synthetic;
new live Windows XYZ/calibration is pending. Do not repeat M0/M2 or treat this
as shared collision. Next: Windows procedure in WINDOWS.md, then inspect
native geometry/material/frame ownership for a collision slice. D005 records
the two candidate routes and why observations precede geometry injection.


**Next source-only M3 geometry gate:** read [M3_GEOMETRY_GATE.md](M3_GEOMETRY_GATE.md).
It records pinned upstream collision memory/partition/lifetime constraints and
explains the new `tools/geometry_preflight.py` / `tests/test_geometry_preflight.py`
synthetic triangle checks. These do not access commercial assets or alter native
collision; a future original-runtime insertion is BLOCKED on real XYZ,
calibration, genuine source geometry, explicit pool-capacity guards and
native ownership evidence.

## 1. Objective and actual state

User goal: a playable **Crash Bandicoot 1 × Super Mario 64** fusion retaining the
original character mechanics, not a skin swap or fake physics engine. Primary
target is Windows 10/11 x64. Work in a feature branch derived from `m0-recon`,
or directly on `m0-recon` when instructed; **do not merge into `main`**.

M0/M1: pinned-source reconnaissance, toolchains, native event seam, original
runtime observations. M2: **real Mario coin-to-Crash native jump demonstration
completed on Windows**, with operator confirmation. The two games are still
independent processes, windows, cameras, collision worlds and renderers.
**M3 next:** determine a verifiable shared-coordinate, shared-visibility and
collision/world-ownership plan; implement the smallest demonstrable step only
after checking actual native interfaces. M4 playable shared slice is NOT DONE.

Fixed upstream source pins:
- CrashBandicoot-Launcher: `224da7757920a817de2d9242416f657ab95782ea`
- sm64ex: `d7ca2c04364a6dd0dac58b47151e04e26887e6f0`
- libsm64 reference: `fd11813208272b4271d92bd92feb8f3fdbe61be5`

No ROMs, BIN/CUE, CHD, commercial game files, extracted assets, generated game
binaries or archive snapshots are in this Git repository. **Do not add them**
via Git, LFS, Issues, PR attachments, Actions artifacts, base64 encoding,
temporary upload or another remote service. Source code in this repository
and pinned upstream open repositories is sufficient for asset-free Cloud work.
Do not download commercial games or bypass licensing.

## 2. Evidence: distinguish source replay from live gameplay

Original local real game run `20261009-151351-877` on Windows 11:
- Mario: native coin `seq=1`, tick 4520, then `seq=2`, tick 4529.
- Crash: matching `received seq=1`; `input_applied seq=1`; second
  received event `observe-only/drop seq=2` due to one-shot keyboard arm.
- Native Crash guest state: **22 samples** with raw vertical Y
  `1387515 → 1546674 → 1387507`, native AIR becoming true and then false,
  GROUNDLAND returning true, and rising/falling vertical velocities.
- User explicitly reported seeing Crash jump when Mario picked up the coin.
  This is a human observation, **not** a video capture or measured latency.
- Original evidence and limitation notes: `docs/EVIDENCE.md`.

Sanitized, source-controlled evidence:
`tests/fixtures/windows_coin_jump_20261009.json`.
It contains 22 raw motion records and correlated event metadata but **no game
assets**. `tests/test_recorded_windows_trace.py` checks sequence/summary/state
consistency; this is **VERIFIED_SYNTHETIC replay**, *not* a fresh runtime run.

`tests/test_native_sender_protocol.py` uses a real compiled production C sender
and localhost UDP to verify its CMJ1 wire format; it does not run either game.
Native Windows `Test-Integration.ps1` already passed 25 fixture/adaptor checks,
including read-only movement observer. `python -m unittest discover -s tests -v`
previously passed 6 bootstrap tests; additional trace/sender tests were added
for the Cloud handoff and require a **fresh current test run**.

## 3. Run as much as possible in Codex Cloud (no commercial files)

1. Check `git status --short`, branch/commit, environment, available tools.
   Do not overwrite dirty files, caches, or previously completed work.
2. Run:
   ```bash
   python -m unittest discover -s tests -v
   ```
   The tests include base config, source-mod installation, recorded native
   trace integrity, and a real loopback C sender. GCC is required for the
   latter; if missing, report **SKIPPED**, install from an authorized package
   source if available, and rerun.
3. Inspect `.github/workflows/source-only-checks.yml` and its results. GitHub
   hosted CI is a **source-only** Python/GCC check, not gameplay testing.
4. Optional when dependencies and time allow:
   ```bash
   bash tools/m0-setup.sh
   bash tools/check_integration.sh
   ```
   These fetch **pinned public source/dependencies** and compile a real source
   translation unit/C sender and upstream .NET mod compiler with fixture RAM.
   They do not fetch game files and do not certify real gameplay.
5. Inspect `integration/crash/CoinJumpMod.cs` and
   `integration/sm64/cm64_coin.c` before changing native ABI/protocol/guards.
   Keep source tests and the existing original behavior passing.
6. For any validation, explicitly label `VERIFIED_SYNTHETIC`,
   `VERIFIED_REAL` (only if *you* actually ran original runtimes),
   `NOT_TESTED`, or `BLOCKED` with logs/revision. Never rebrand the user's
   earlier original-runtime results as a new Cloud execution.

## 4. How to validate the original games lawfully

**Cloud cannot automatically see local Windows files.** The Windows machine
has legitimate user-supplied local data and an already prepared build under
`%LOCALAPPDATA%/CrashMarioFusion/M0`; this data stays there.

Use **Codex CLI on the Windows machine**, an explicitly authorized local
computer connector, or have the operator execute and report the test.
A GitHub-hosted runner **does not** have access to that Windows data; merely
connecting GitHub to Codex Cloud does not create such access.

Windows commands from PowerShell 7 in the repository root:
```powershell
./tools/windows/Test-Integration.ps1
$env:GALLIUM_DRIVER = 'llvmpipe'
./tools/windows/Start-Integration.ps1 -CrashDisc "<private-own-disc.cue>" -Apply -KeyboardArm -Seconds 900
```
In Crash's unpaused level, tap **W** (R1) and release, then switch to Mario
and pick up one yellow coin within 60 seconds. Correlate
`coin`, `received`, `input_applied`, `motion_sample`,
`motion_summary` and visible landing. The software GL fallback is
application-local and can be slow; original Windows audio endpoint was absent
in the earlier remote session.

This successful test has already been done by the user; **do not require
repetition just to acknowledge M2**. A deliberately passive control
(`-Apply` omitted) is still a useful additional causal-isolation test.
Never commit local logs containing disc paths, executable dumps, secrets or
user identifiers without review/sanitization.

## 5. Next scoped engineering work — continue toward M3

**Work, don't merely restate a plan.** With source-only access, first run the
new tests; fix genuine failures and improve deterministic regression coverage.
Then examine source-level world-coordinate and object/collision seams of both
pinned engines, comparing at least two viable preservation-first approaches.
Record the evidence and tradeoffs in `docs/DECISIONS.md`; escalate a hard
architecture decision to Astra only when actually available and necessary.
Do not assume `libsm64` has full Mario interactions; see D002.

Implement the **smallest testable, reversible M3 proof**, such as an asset-free
coordinate/unit/frame transform contract with round-trip, invariance and
bounds tests, **only if grounded in real source units and documented
assumptions**. No arbitrary engine scale or invented game collision.
Avoid writing another game engine, merging arbitrary player RAM, or claiming
one world merely because one window overlays the other.

Required acceptance/report:
- Source-only Python + production C loopback tests rerun, exit status shown.
- Native integration tests where the environment actually supports them;
  otherwise a reproducible local Windows handoff, clearly `BLOCKED`.
- Original Mario coin/healing/delete and Crash movement preserved by design.
- No non-public game files in commits, caches pushed to Git, or CI artifacts.
- Exact source files changed, command/output, and evidence classification.
- Update `docs/STATUS.md`, `docs/EVIDENCE.md`, and decisions if materially
  changed. Preserve `m0-recon` history and keep `main` unchanged. Open a PR
  when the testable M3 increment is ready, without automatic merge.
- **No playable-fusion claim or Release/ZIP until real shared-world gameplay
  is implemented and verified on native Windows.**
