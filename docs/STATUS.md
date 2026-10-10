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

## M3.1 native Mario runtime gate — 2026-10-09 (updates previous native new-telemetry NOT_TESTED)
M3.1 PARTIAL, may advance to Crash continuous pose work: user executed the newly compiled Mario CMW1 collector during real gameplay. VERIFIED_REAL (without independent visual claim): 1,137 native post-update packets, 0 rejected, native level=16 area=1; XYZ variation in all axes (441 distinct XYZ positions), native ACT_WALKING / ACT_JUMP / ACT_DOUBLE_JUMP / ACT_TRIPLE_JUMP values; contiguous packet sequence, one session, 5 observer epochs, observed max 9 arrivals per sliding second, and a 4.7-second no-frame gap compatible with but not proof of the user's pause. No native area change verified (all samples area 1). Only game log issue: non-fatal missing Windows WASAPI endpoint. No evidence of a telemetry error. Crash continuous pose adapter, absolute frame correspondence, pause causality test, area-change lifecycle, native colliders and shared gameplay remain BLOCKED/PENDING. Original prior M2 42 Crash samples still separate. No private logs or assets in Git.

## M3.2 diagnostic continuous Crash pose increment — 2026-10-09
Codex authored a separate opt-in Crash CMW1 diagnostic emitter plus read-only private Windows localhost collector; an independent reviewer completed testing and private build. M3.2 is **VERIFIED_SYNTHETIC/native-build**, NOT yet tested in the actual Crash game. Source C# mod integration/crash_pose/CrashPoseMod.cs is disabled by default, has bounded nonblocking local UDP emission (<=10 Hz, <=300 s, <=3000 attempts), emits signed native XYZ and rotation and level, validates player pointer/context/paused flags and invalidates observer-local epochs at level, object-lifecycle or pause changes. It NEVER writes guest RAM or input. Critically it samples from PadReadEvent, not a proven post-physics seam: CMW1 phase=0 UNKNOWN_DIAGNOSTIC and callback count are **NOT** a native physics tick. Calibration remains blocked.
Windows QA: 7/7 new Python pose tests PASS; full Python suite 49/49 PASS; native Crash mod compiler with actual pinned RecompOne event bus and fixture RAM 58/58 assertions PASS, with unchanged RAM/inputs and no extra VBlank memory effects; original M2 regression 27/27 PASS; original geometry fixture oracle 17/17 PASS. Private generated Crash Windows launcher compiles with 0 errors/0 warnings, fixed-source pin verified and sealed collector manifest accepted. The original pinned Crash git checkout, original project worktree and M2 mod remain unchanged. No original game was launched for this increment, no new native pose packets yet. PR remains draft, no merging into main or m0-recon. See docs/EVIDENCE.md and docs/WINDOWS.md.
# Latest source-only reference-box increment

Branch `feat/m3-reference-box` derives from migration checkpoint `a43ee9b` on
`feat/m3-coordinate-contract`; all existing M3.1/M3.2 work preserved.
Authored c1 leaf-to-top-boundary converter and original-reference/native-Mario
comparison implemented. **54 Python tests PASS, no skips**, **58 Crash pose
fixture assertions PASS**, **27 original bridge checks PASS**, **13 PowerShell
ASTs parsed** on Cloud Linux. All new evidence VERIFIED_SYNTHETIC.
Overlapping support differs (c1 reference 40 vs Mario 48), blocking general
equivalence. New Windows test script NOT_TESTED; no game/old PC executed.
M3.2 actual Crash diagnostic packets remain pending on the new computer, then
coherent post-physics sampling/geometry provenance/calibration/capacity gates.

Implementation published in [draft PR #4](https://github.com/kauankelvin7/crash-mario-fusion/pull/4),
base feat/m3-coordinate-contract. Source-only CI 37987762871 PASS for1571f25.
Original main, m0-recon and base feature remain unmerged.

## Issue #5 P1/P2 — Cloud implementation (2026-10-09)
On existing `feat/m3-offline-preflight` from a43ee9b: delivered two-slot read-only
CMW1 observation correlation with independent sessions/frames, explicit common
receiver clock, typed rejection and lifecycle gates; delivered positive uniform
scale/Y-yaw/origin least-squares FrameMap estimator with explicit landmark
provenance, conditioning, holdout, numeric and residual gates. **VERIFIED_SYNTHETIC**:
65/65 Python tests (16 new), 58/58 pinned Crash observer assertions, 27/27 M2
fixtures, 13/13 PowerShell ASTs on Linux; independent QA approved the bounded
P1/P2 scope. PR CI now also targets `feat/m3-coordinate-contract`.
New Windows command: `./tools/windows/Test-OfflinePreflight.ps1`; native Windows
execution of this increment is **NOT_TESTED**. No game was launched, no commercial
files used, no physics/input/collision modifications. Physical synchronization
and calibration remain **BLOCKED**. M3.2 remains diagnostic; no new VERIFIED_REAL
evidence, native collider or shared playable world. PR #4 is separate and Issue
#3 is not declared complete. Do not merge main or publish a playable Release.

## M3.3 — consolidated integration and native observation preparation (2026-10-09)
`feat/m3-integration-observer` starts at real base a43ee9b and contains complete
PR #4 head 0cdc0ea and PR #6 head b74b6c7 by local branch merges. Both historical
document sections survive conflicts; GitHub PRs remain unmerged. Main/m0-recon
and original native physics/input adapters are unchanged. One discover-based CI
runs both pinned sm64ex and c1 sources plus all CMW1/calibration tests.

Implemented passive common-clock two-engine CMW1 collector with fixed counters,
finite private logs, independent bindings and source-loss/age/continuity/frame/
pause diagnostics; explicit geometry composition now checks estimation scope
before applying the authored reference converter. Invalid descriptor sizes now
raise controlled ValueError. No automatic transition matching, input writes,
real collider or gameplay claim. **VERIFIED_SYNTHETIC**: 82/82 Python tests (all
70 consolidated previous tests + 12 new), 58/58 Crash observer assertions,
27/27 M2 fixtures, 15 PowerShell ASTs; both public collision oracles run with
Linux ASan/UBSan. New Windows workflow/paired runtime collection **NOT_TESTED**.
Physical synchronization/calibration remain **BLOCKED**. Next: operator-run
three-terminal passive receipt experiment on new Windows PC, per WINDOWS.md.

## M3.5 — local private paired-capture consistency audit (2026-10-09)

Branch `feat/m35-capture-audit` from verified M3.4 source-only Windows CI head adds `tools/audit_paired_capture.py`, bounded self-consistency inspection of a finished private paired receiver JSONL + summary, and deterministic regression tests. It validates clock-domain monotonicity, two-engine admitted-sequence holes, receiver arrival gaps, counters, finite file/row budgets and fail-closed evidence labeling. Output contains anonymous aggregates only; it does NOT verify that packets originated from running games, measure source latency or validate postphysics/native area generations. Original adapters, game behavior, public pins and original private files remain unchanged. Local Windows original-game paired receiver experiment, authentic correspondences, and native collision/rendering remain BLOCKED. See docs/M35_CAPTURE_AUDIT.md. GitHub Actions CI for this increment must be checked separately before classifying regression status. Keep PR draft and unmerged.


## M3.5 native Windows local preflight and original-runtime gate — 2026-10-09

Latest branch `feat/m35-capture-audit` received narrow Windows setup fixes: `tools/windows/Setup.ps1` now installs and verifies native MinGW64 Python in addition to MSYS Python, and `Test-ReferenceGeometry.ps1` fixes Git's source-only line-ending interpretation via process-scoped `core.autocrlf=input` (no upstream content rewritten). Local original-game files remained exclusively on the authorized Windows machine; none were committed or uploaded. The original project checkout remained clean.

**VERIFIED_SYNTHETIC/native Windows x64:** `Test-ReferenceGeometry.ps1 -FullSuite` passed **87/87 Python tests with zero skips** using native MinGW64 Python/GCC, pinned public sm64ex and c1 source collision oracles. `Test-Geometry.ps1` passed **17/17**; `Test-CrashPose.ps1` passed **58** compiled RecompOne event-bus/RAM assertions; `Test-Integration.ps1` passed **27** original C sender to Crash fixture assertions. `Test-OfflinePreflight.ps1` passed and still marks synthetic math `calibration_ready=false`. Hosted source-only Linux and Windows Actions on `5f0182d` both SUCCESS; no hosted game execution.

**VERIFIED_REAL — startup/graphics only, NOT gameplay:** the pinned RecompOne-based private Crash diagnostic launcher built successfully, sealed, identified a locally provided compatible disc, JIT-recompiled the guest and opened a responsive native **OpenGL 4.3** window. The independent read-only Crash CMW1 diagnostic mod reported `ready` with phase UNKNOWN_DIAGNOSTIC. A finite **90-s original-runtime diagnostic session received 0 valid pose packets**, so actual in-level movement, pause/transition behavior, coherent postphysics capture and any calibration remain **NOT_VERIFIED**. This must not be represented as a successful live pose capture.

**VERIFIED_REAL — executable initialization only:** the private instrumented sm64ex Windows build succeeded from a locally SHA1-verified owned US ROM (includes `cm64_coin.o` and `cm64_pose.o`). An explicit **45-s dual-process run** on this PC exited 0 with Mario and Crash launched, Crash CMJ1 receiver ready, `Apply=False`, no actionable input and no evidence of a real Mario coin causing a Crash action in this session. Mario independently opened a responsive native OpenGL window. Game launch is not shared world or shared collision. The user's earlier **M2 real coin-triggered Crash jump** remains a separate historical verified result and was not repeated here.

Remaining real gate: operator drives Mario and Crash into actual unpaused gameplay, produces continuous pose packets with known engine-local identity and visible player motion; record pause/area changes; then investigate/prove Crash's native postphysics ownership, independent corresponding 3D landmarks, real source collision volume/material/generation and bounded Mario pool occupancy/lifetime before any shared collision experiment. Keep PR draft, preserve original solvers/inputs; never merge main or distribute playable release yet.

**M3.5 follow-up, private Mario CMW1 collector on current Windows PC:** original instrumented Mario launched with a responsive OpenGL game window during a finite **55-second** collection, but yielded **0 accepted / 0 rejected pose packets** without operator-confirmed gameplay. This is **NOT_VERIFIED live pose**, regardless of the former process exit code 0. The collector previously reported apparent CLI success even with zero frames; `tools/collect_pose.py` now fails closed on empty captures while preserving the local `summary.json`, with an explicit regression in `tests/test_live_pose.py`. Local current-head full native Windows source-only suite **88/88 tests PASS, zero skips**, still VERIFIED_SYNTHETIC. Do not treat either game's startup as validated player-motion telemetry. Both games' test processes were terminated by the finite local runners.

## M3.6 — native Windows operator pose gate (2026-10-09)

New stacked draft branch `feat/m36-operator-pose-gate`, based on M3.5 PR #9, adds `tools/windows/Run-PoseGate.ps1`, focused regression tests, and `docs/M36_OPERATOR_GATE.md`. Read-only explicit original-game capture is finite and fails closed on empty logs; `-CheckOnly` validates the sealed Crash launcher or pinned private Mario generated source manifest **without** launching any game. Local Windows preflights for both engines returned exit 0 with **zero games started**; an invalid disc path returned exit 1. Native Windows full source-only suite **90/90 PASS** on initial head; current extended manifest verification also passed both Windows preflights. New hosted CI results must be checked separately. All live player-motion CMW1 and any physical calibration remain **BLOCKED** until actual in-level gameplay generates packets. Original runtimes/collision solvers and `main` unchanged; no private files published.


### M3.6 original-runtime in-level receiver captures (2026-10-09)

**VERIFIED_REAL runtime-origin receiver frames (on authorized Windows PC, operator played):** read-only `Run-PoseGate.ps1` captured **Mario 708/708 admitted** (0 rejected, 0 sequence gaps, 205 distinct native XYZ positions, 202 consecutive within-epoch changes, levels 6/16, area 1, five observer generations, 100.4 s first-to-last receipt) and **Crash 1409/1409 admitted** (0 rejected, 0 sequence gaps, 744 distinct signed native raw XYZ positions, 760 consecutive within-epoch changes, level 9, six observed epoch IDs, 157.8 s first-to-last receipt). Both collections stopped within their respective 180 s bounds with exit 0 and had summary totals consistent with their private JSONL row counts. Both games closed afterward. This **supersedes the previous zero-frame startup-only gate**, not the remaining physics/collision restrictions.

**Known evidence limits:** Crash still emits on `PadReadEvent` in `UNKNOWN_DIAGNOSTIC` phase, *not* demonstrated native postphysics. Four unusually large within-epoch Crash raw-position jumps (greater than 1,000,000 raw units) were observed, all at state transitions, including 22/23 → 40; they need scene/state provenance before interpreting positions as continuous physical motion. Neither collector output contains paused frames; pause handling or causal timing was not proved. Mario float32 positions and Crash signed raw fixed-point-like positions are **not directly comparable or calibrated**. The separate runs have distinct random sessions and independent receiver clocks, **not a paired common-clock capture**. `calibration_ready=false`, `live_gameplay_verified=false` in original collector summary, no claim of correspondence, cross-engine physics, shared surfaces or playable fusion. All original capture files remain private in local appdata; only aggregate anonymized diagnostics are documented here.


## M3.7 — first audited dual original-game receiver capture (2026-10-09)

**VERIFIED_REAL receiver-only:** on authorized native Windows, Crash and Mario were both launched with independent private sessions into a single monotonic UDP localhost receiver for a bounded 180 s. Initial strict-epoch run had 2,116 arrivals but only Crash 1 admitted (2,115 frame mismatches). Opt-in, whitelisted, increasing-epoch rebind then produced **2,204 admitted packets**: Crash **1,187**, Mario **1,017**, **0 rejects/sequence holes**, and **1,108 status rows** with both receiver slots fresh. Private audit returned **CONSISTENT** after fixing its rebind arrival-gap baseline and checking encoded frame epoch; original files/logs/tokens remained local. **94/94 native Windows source/oracle tests PASS**. See `docs/M37_LIVE_CAPTURE.md` and draft PR #11. Source-delay, Crash postphysics ownership, world-frame correspondence, calibrated geometry, merged collision and playable fusion remain **BLOCKED/NOT_TESTED**; `main` unchanged.
