# Execution status

Date: 2026-10-09. Branch: `m0-recon`. Project base: `d45ffef659f606a779e158275e098947ba2ecd7c`.

- M0 reconnaissance: completed; six pinned upstream sources inspected. See [EVIDENCE.md](EVIDENCE.md).
- Architecture: CONDITIONAL, Astra-reviewed D002; favor complete Crash Launcher + sm64ex for passive observation. A narrow loopback event adapter is now implemented; shared-world transport/physics remain unvalidated.
- Model routing: runtime supports explicit delegation/model overrides. Automatic `.codex/agents/*.toml` loading and root model/reasoning selection remain unverified; static tests establish file contents only.
- Astra subagent invocation: once, explicit `spawn_agent(model="gpt-6-astra", reasoning_effort="high", fork_turns="none")`; `/root/astra_architect` returned its verdict. Selection follows the runtime tool contract; no additional resolved-model telemetry is exposed. This does not prove automatic TOML routing.
- Recon: two bounded read-only tasks, Crash and Mario. Root alone edited shared files; gate QA audit recorded separately.
- Launcher Linux and libsm64 builds: VERIFIED_SYNTHETIC (build/toolchain validation).
- Bootstrap: 3 static tests; libsm64: 7 synthetic collision checks; upstream DiscCheck synthetic suite passed.
- Original game data: BLOCKED; owned Crash NTSC-U SCUS-94900 disc and SM64 US ROM absent from selected project/cache paths.
- Original Crash gameplay: BLOCKED by owned data; only launcher CLI exercised.
- Original Mario gameplay/full sm64ex build: BLOCKED by owned ROM.
- Graphics: NOT_TESTED; DISPLAY and WAYLAND_DISPLAY absent. This does not establish GPU or software-rendering availability.
- Real shared-world event: NOT_TESTED
- Synthetic cross-runtime event: VERIFIED_SYNTHETIC for authored C sender → upstream Crash mod compiler/pad bus using fixture RAM; neither original gameplay runtime ran. M0 collision checks remain single-library tests.
- c1 full build: BLOCKED by missing GNU/i386 headers/dependencies; optional reference candidate. Assetless boot is unsafe because its stream reader assumes a valid file.
- Environment reproduction: `bash tools/m0-setup.sh`, then `bash tools/m0-check.sh`; retained sources/dependencies under `/workspace/.cache/crash-mario-m0`. Draft persistence/publication is separate from runtime validation.

Next: M1 passive native-event/tick observation and ownership contract, on a lawful test machine with owned data. Compare instrumented/uninstrumented SM64 coin pickup; identify Crash logical update/input seam across pause/loading. No fusion or gameplay fidelity is claimed.

Primary target: Windows 10/11 x64. Native Windows builds/gameplay: NOT_TESTED (no Windows runner here). Eight PowerShell scripts provide setup/build/test/start and paired adapter execution; AST parsing on PowerShell 7.5.4/Linux and non-Windows platform guard passed. See [WINDOWS.md](WINDOWS.md). Linux results remain cloud-only.

QA gate: M0 Linux evidence PASS; Windows preparation by syntax/dependency inspection PASS after adding GLEW. Windows native build/run NOT_TESTED; original gameplay/fusion BLOCKED. Saved install_script/start_skill draft confirmed; publication and new-task restoration NOT_TESTED.

Continuation after M0: branch published to `origin/m0-recon`, preserving `6e21f41`. Authored native SM64 coin observer and Crash source mod are implemented; local UDP connects native state observation to the existing native controller bus. Native interaction translation unit and C sender compile on Linux; actual upstream mod compiler/event bus pass fixture tests. VERIFIED_SYNTHETIC only. Windows Build/Test/Start-Integration scripts prepared; native Windows and real cross-game event still NOT_TESTED/BLOCKED by owned data and execution platform. No playable shared-world fusion yet. Next action: run the passive/apply Windows pair in WINDOWS.md, review native consequences/jump/landing before advancing collision/rendering. Distribution is deferred until genuinely playable.

## Windows local validation — 2026-10-09 (supersedes earlier NOT_TESTED lines)

- Windows 11 x64: pinned .NET Crash Launcher compiled; native instrumented sm64ex compiled using explicit Windows Makefile flags. Real local game runtimes both initialized with application-local Mesa llvmpipe; system display driver was not changed.
- Crash recognized the expected NTSC-U disc identifier, completed recompiler/pipeline, loaded source mod and reported `[Host] OpenGL window ready` and `[cm64] receiver ready` in the paired run.
- Mario created a responsive native Windows window and remained alive during a short startup test. Its original GL path first crashed in `gfx_opengl_init`; private Mesa software renderer avoided that crash.
- `Test-Integration.ps1`: 14/14 native Windows fixture checks passed (VERIFIED_SYNTHETIC). Windows Python: 6/6 passed (VERIFIED_SYNTHETIC).
- A passive paired run (`Start-Integration.ps1`, Apply=False, 45 seconds) launched both real processes, each with a responding window, and exited with code 0. No Mario coin pickup event or resulting Crash jump occurred or was witnessed. **Real gameplay interaction, jump/landing, shared worlds/collisions/camera remain NOT_TESTED**. Native startup is VERIFIED_REAL only for boot/window/readiness, not gameplay.
- Windows host reported no usable audio endpoint for both runtimes; runtime audio remains unverified. Mesa llvmpipe is a testing fallback, not proof of acceptable gameplay performance.
- `--smoke` can return success while graphics initialization failed; do not use its exit code alone as a graphics oracle. Next: instrument coin pickup + Crash grounded/jump/landing in a controlled real-game interactive session, with actual footage/observations; only then mark VERIFIED_REAL gameplay.

## Latest M2 gate — 2026-10-09 (supersedes earlier M0 statuses)

- VERIFIED_REAL Windows: native Mario yellow-coin pickups were delivered to native Crash runtime by CMJ1 UDP; in apply/keyboard-arm mode real Crash logged `input_applied seq=1`, with the next sequence correctly suppressed by single-use authorization.
- VERIFIED_SYNTHETIC Windows: 25/25 bridge/probe assertions and 6/6 Python regression tests passed. New diagnostic reads the native Crash player position/velocity/state/air/ground flags for 3.5 seconds after a pulse, with no game memory writes. See EVIDENCE and WINDOWS for exact fields and oracle.
- NOT_VERIFIED: Crash actually leaving the floor and landing in reaction to Mario, shared world/physics/collisions/camera, audio and overall playability. Do not mark the fusion playable or publish Releases.
- Next: one real keyboard-armed paired run; correlate `coin`, `received`, `input_applied`, `motion_sample`, `motion_summary`, plus direct visual movement. Only then plan the minimal shared-world prototype.

## Native Windows movement confirmed (2026-10-09)

Real Windows session `20261009-151351-877`: Mario two native coin events reached Crash; first applied native controller Cross, second was observe-only. Live Crash guest player object provided 22 movement samples with raw vertical position climbing from 1387515 to 1546674 and returning to 1387507, AIR flag transitioning true then false and GROUNDLAND returning. Classification: VERIFIED_REAL for recorded guest jump and landing sequence following cross-game input. A control run and independent visual confirmation would strengthen causal attribution. Unified world, collisions, camera and final playable fusion are NOT IMPLEMENTED; no release. Full values in EVIDENCE.md.

## Confirmed visual result: Mario coin → Crash jump (2026-10-09)

**M2 interaction demonstration PASS (VERIFIED_REAL + operator-reported visual corroboration):** Mario coin `seq=1` was sent and received by the actual Crash runtime, applied as guarded native Cross; Crash guest memory recorded a full rise, airborne movement, fall and grounded return (22 samples). The user confirmed they saw Crash jump concurrently with the Mario coin pickup. The visual part is a firsthand user report, not video evidence; latency was not independently measured. The second coin did not trigger an additional jump.

**Not yet the requested fusion:** worlds, geometry, collisions, camera and renderer remain separate. Recommended next engineering gate is a brief no-Apply control scenario, then design a minimal shared-coordinate, visibility and collision prototype with native-world authority and explicit ownership; do not claim a unified game until validated. Keep `main` unchanged until authorized.
# Current M3 increment — 2026-10-09

M2 Windows result remains confirmed as recorded in CODEX_HANDOFF/EVIDENCE.
Feature `feat/m3-coordinate-contract`, based on `m0-recon` at `38bb594`:
signed native Crash XYZ + level observation, explicit calibrated read-only
Crash-to-Mario mapping, inverse precision check, native floor-query bounds,
and private Windows preflight command. Cloud Python **17/17 PASS**;
upstream mod compiler/native C/event bus with fixture RAM **27 checks PASS**;
**9 PowerShell ASTs parsed** on Linux. These are VERIFIED_SYNTHETIC.
New XYZ/calibration on real Windows: NOT_TESTED. Shared collision, rendering
and playable fusion remain NOT IMPLEMENTED. See WINDOWS for next local test.

## M3 Windows preflight + PR update

Branch `feat/m3-coordinate-contract` is in [draft PR #2](https://github.com/kauankelvin7/crash-mario-fusion/pull/2) targeting `m0-recon`; proxy-related PR creation blockage is **RESOLVED** via the GitHub connector. Source-only GitHub Actions CI is green. On native Windows: Python 17/17, adapter fixture 27/27, PowerShell AST 9/9, private Crash/SM64 build and synthetic coordinate preflight all PASS. These M3 tests remain **VERIFIED_SYNTHETIC**, even when run on Windows, because actual XYZ game movement / landmark calibration are not yet evidenced. A paired real-game session was launched with two responsive windows; new XYZ samples not yet obtained. Shared geometry, collisions and rendering remain UNIMPLEMENTED. Keep PR draft and main unchanged until the real XYZ and operator-chosen calibration are validated.

## Offline M3 geometry readiness — 2026-10-09

While the Windows games remain closed, advanced `feat/m3-coordinate-contract` with source-only `tools/geometry_preflight.py` and `tests/test_geometry_preflight.py` (8 new synthetic geometry checks). Hosted CI passed [run 37957543671](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37957543671), preserving the existing C/UDP/coordinate tests. Examined actual pinned Mario `Surface`/partition/allocator seams: s16 vertices, cell fan-out and ineffective native pool overrun guards mean **no collision insertion is authorized yet**. See `docs/M3_GEOMETRY_GATE.md` for source-backed ownership/capacity requirements and future local validation sequence. **VERIFIED_SYNTHETIC** for pure preflight only; native XYZ, calibration, Crash geometry source, native colliders, rendering and combined world remain **NOT_TESTED/UNIMPLEMENTED**. Keep draft PR #2, `m0-recon` and `main` unchanged.

## Current M3: original collision-code oracle and pose protocol

Cloud Linux: **34 tests PASS**, including actual full-sm64ex loader/floor
queries with authored geometry and bounded fixture pools, six type/yaw cases,
ASan/UBSan, capacity rejection and native dynamic cleanup. Geometry preflight
now includes s32 normal/s16 padding safety, cell fan-out, explicit synthetic
materials and pool planning. CMW1 adds tested native position/rotation/state
encoding and bounded deterministic snapshot storage; no live emitters or pose
writes. **10 PowerShell ASTs parsed**; new Test-Geometry launches no games.
All new validation is VERIFIED_SYNTHETIC; native Windows increment NOT_TESTED.
D006 records fresh Crash octree-vs-Mario triangle evidence and conditional
Astra recommendation. Live geometry/collisions/rendering remain unimplemented.
Next: source-only authored box oracle, then authorized private Windows layout,
XYZ/calibration and pool/lifecycle observations before a real collision slice.

Published implementation `857a6a1`, draft PR #2 updated (base m0-recon).
Hosted source-only CI [37959761599](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37959761599)
passed; job/test-step success verified via API. Detailed hosted log download
is proxy-blocked; local test evidence above is retained. No main merge.

## Live M3 Windows observation — 2026-10-09 (supersedes older XYZ NOT_TESTED status)
New authorized native Windows run: Crash received two real Mario coin events, applied one armed native Cross pulse, captured 22 real guest-player XYZ samples and level 9, with rise/fall, AIR and GROUNDLAND transitions. Live XYZ field observation is VERIFIED_REAL, but X and Z remained constant in every sample: real horizontal movement, units and axis mapping are NOT_VERIFIED. Mario area identity and calibration anchors still unknown. No native collider, geometry provenance, dynamic pool occupancy, shared camera/rendering or playable fused world. No new visual-confirmation claim or copyrighted/private files shared. PR remains draft; no merge.

## Follow-up native horizontal-coordinate evidence — 2026-10-09
Further real authorized Windows gameplay in the same session established **4 Mario native coin receipts** and **2 guarded Crash input applications** (seq 1/3); seq 2/4 were properly observe-only/dropped. A total of **42 real XYZ samples** span two observed native Crash jumps and two initial distinct XZ locations. During the second 20-sample capture, Crash X changed an additional +2048 raw units after landing: real field variation VERIFIED_REAL, at least 3 unique recorded XZ positions. Crash level 9 throughout. This supersedes the earlier statement that horizontal XZ was only constant, but does not establish conversion from raw units, accurate continuous walking track, shared landmarks or cross-engine mapping. Original collision/geometry and fused play remain unimplemented. Keep privacy boundary and draft PR unchanged.

## M3.1 — native Mario-only pose telemetry prototype (2026-10-09)
A bounded, opt-in native Mario CMW1 pose emitter has been implemented and compiled into the privately generated Windows sm64ex runtime. An operator-controlled localhost collector accepts only current-session valid observations and stores finite logs outside Git. The source patch runs after the native Mario update during normal unpaused gameplay; level/area transitions invalidate its observer epoch. Original CMJ1 coin event adapter remains separate. No continuous native Crash emitter was added because its current controller-polling seam is not proven to be a coherent post-physics snapshot. **M3.1 is PARTIAL:** both-engine pose sync, calibrated world correspondence, collisions, shared camera and unified game remain unimplemented.

Verification on Windows 11: new native sender/source-hook tests **8/8 PASS**; full Python suite **42/42 PASS**; Test-Integration **27/27 PASS**; Test-Geometry **17/17 PASS**; Windows Build-Integration compiled private Mario executable, explicitly including cm64_pose.o in the final link, and .NET Crash launcher succeeded with zero build errors. These are **VERIFIED_SYNTHETIC/native-build**; actual gameplay of new pose emitter is **NOT_TESTED**. Existing M2 real gameplay/42 XYZ samples are separate earlier evidence and are not a test of new telemetry. No main/m0-recon merges; draft PR remains.
