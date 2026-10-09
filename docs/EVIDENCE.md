# Evidence ledger

Classifications:

- `VERIFIED_REAL`: tested with running original/recompiled licensed game runtime(s).
- `VERIFIED_SYNTHETIC`: tested using fixtures/mocks or standalone harness without both real runtimes.
- `NOT_TESTED`: no actual command/run.
- `BLOCKED`: specific missing condition; include how to unblock.

For each result: date, revision(s), command, environment, expected, actual, classification, log link/path, investigator. Avoid reporting `VERIFIED_REAL` based on a compile, static scan, mock, visual overlay or invented transcript.

## M0 — 2026-10-09, Codex Cloud Linux x86_64

Project base `d45ffef659f606a779e158275e098947ba2ecd7c`, branch `m0-recon`. GCC 14.2.0, Python 3.12.14, .NET SDK 10.0.401, chdman 0.276. Investigators: root; bounded read-only crash_recon/mario_recon; one explicitly selected gpt-6-astra architecture task. No auto-loaded project agents or root model selection claimed.

| Source | Exact inspected HEAD | Static entry/seam, relative to source |
| --- | --- | --- |
| rehan-remade/universal-modder | `8370faa8e114baf33acdb23079aff552a7728c4b` | `skills/mashup-mods/SKILL.md`, its `references/mashup-cases.md`; technique notes listed below |
| Matteo842/CrashBandicoot-Launcher | `224da7757920a817de2d9242416f657ab95782ea` | `CrashBandicoot.Launcher/Program.cs:12`; `Recomp/GameLoader.cs:88`; `RecompOne.Runtime/Runtime.cs:128`; `Modding/HookManager.cs:103`; `Events/PadInput.cs:15` |
| wurlyfox/c1 | `256fdcef59f15a190290cc19db3fa9a707843b69` | `src/main.c:135` CoreLoop, `:268` GoolUpdateObjects; `src/gool.c:3376` GoolSendEvent, `:3694` GoolCollide; `src/ns.c:224` NSFileReadRange |
| n64decomp/sm64 | `9921382a68bb0c865e5e45eb594d9c64db59b1af` | `src/game/game_init.c:643` thread5_game_loop; `src/game/mario.c:1699` execute_mario_action; N64 ROM target |
| sm64pc/sm64ex | `d7ca2c04364a6dd0dac58b47151e04e26887e6f0` | `src/pc/pc_main.c:86` produce_one_frame; `src/game/level_update.c:963`; `src/game/interaction.c:739` interact_coin |
| libsm64/libsm64 | `fd11813208272b4271d92bd92feb8f3fdbe61be5` | `src/libsm64.h:145`; `src/libsm64.c:101` ROM init, `:221` tick; `src/decomp/game/interaction.c:66` no-op mapping |

Read upstream `knowledge/techniques/{choosing-a-mashup-route,evidence-levels-for-mashup-claims,oracles-how-agents-know-a-mod-works,bridge-contracts-ownership-units-and-lifecycle}.md`. Nearest prior project inspected: libsm64; its hosts remain creator reports. `um` CLI absent: bounded local knowledge-tree searches used instead; no Crash-specific note found by that search. libsm64 importer pins geometry source to sm64 `06ec56df7f951f88da05f468cdcacecba496145a`; no ROM fetched. Generated upstream source stays in its ignored cache, never project Git.

### Actual commands and results

Working directory for upstream commands is `/workspace/.cache/crash-mario-m0/<source>`; SDK command is `/workspace/.cache/crash-mario-m0/dotnet/dotnet`. Complete logs retained under that cache's `logs/`; compact committed output: [m0-results.txt](evidence/m0-results.txt).

| Command / directory | Expected and actual result | Classification |
| --- | --- | --- |
| `git ls-remote origin HEAD` / project | Read succeeded, project base SHA returned via existing Git proxy; no token requested | VERIFIED_SYNTHETIC (access only) |
| `make -j2 lib` / libsm64 | Shared library compiled, exit 0; upstream warnings remain; no ROM/SDL/GLEW needed for library | VERIFIED_SYNTHETIC |
| `dotnet build CrashBandicoot.Launcher -c Release -f net10.0 -p:TargetFrameworks=net10.0` / Launcher | Linux launcher/runtime/recompiler compiled, exit 0; initial successful build: 6 warnings, 0 errors | VERIFIED_SYNTHETIC |
| `dotnet CrashBandicoot.Launcher/bin/Release/net10.0/CrashBandicoot.dll --help` / Launcher | Expected CLI help displayed, exit 0; no game launched | VERIFIED_SYNTHETIC |
| `python -m unittest discover -s tests -v` / project | 3 static configuration/status tests passed | VERIFIED_SYNTHETIC |
| `bash tools/m0-check.sh` / project | Compiles C consumer with warnings as errors, executes 7 assertions: floor, outside miss, dynamic platform, move, delete, replace, unload; no global_init/Mario tick/ROM | VERIFIED_SYNTHETIC |
| `dotnet run --project tools/CrashBandicoot.DiscCheck -c Release -- /workspace/.cache/crash-mario-m0/mame/usr/bin/chdman /workspace/.cache/crash-mario-m0/disc-check` / Launcher | All synthetic checks passed: 5 codecs, 2 pregaps, sectors/concurrency/bounds, malformed/non-CD/multitrack/parent rejection. Optional owned-disc branch not run | VERIFIED_SYNTHETIC |
| `gcc -m32 -fsyntax-only -fplan9-extensions -Isrc src/util/list.c` / c1 | Missing `bits/libc-header-start.h`; full i386 build not run | BLOCKED (optional candidate) |
| Full sm64/sm64ex build, real game boots, shared event | No owned files; not executed. Graphics support not validated | BLOCKED / NOT_TESTED, see STATUS |

Corrections: documented Launcher `-f net10.0` alone failed NETSDK1100 during multi-target restore; command-line TargetFrameworks override fixed it without source edits. Initial collision probe assumed SM64 sentinel -11000; pinned libsm64 `surface_collision.h:13` defines -110000, so corrected expected value and reran; no assertion removed. System APT writes failed (UID1000, no sudo); snapshot.debian.org denied by proxy. User-space APT with Debian signed trixie metadata at deb.debian.org succeeded; downloaded/extracted mame-tools and missing libutf8proc3 locally with TLS, signature and checksum validation intact. No system packages installed. Dotnet channel lookup met ci.dot.net 403; supported builds.dotnet.microsoft.com feed installed 10.0.401. Saved script pins that version directly. Distinct diagnoses, no blind retry loop.

Reproduction: from `/workspace/crash-mario-fusion`, run `bash tools/m0-setup.sh`, then `bash tools/m0-check.sh`. Setup refuses dirty/wrong-revision source caches; keeps generated outputs outside project. Existing network policy allowed GitHub/raw.githubusercontent.com, dot.net/builds.dotnet.microsoft.com, NuGet and deb.debian.org operations; no secret requirements or network policy replacements needed. No credential values saved. Tracked upstream trees clean before/after builds; ignored outputs expected. Project edits are the authorized development work, distinct from installation.

M0 requires these asset-free checks; c1 and N64 builds are optional alternatives. Current-instance/repeat-run validation does not establish fresh-task restoration or publication. Real tick/event/rendering/world mapping/fidelity remain unvalidated. Owned-data tests belong on a lawful local test machine; no retail data should be uploaded/downloaded for this setup.

Windows preparation: five `tools/windows/*.ps1` ASTs parsed with PowerShell 7.5.4 on Linux; Setup.ps1 correctly exits 1 with the native-Windows guard before any cache writes. VERIFIED_SYNTHETIC, not a Windows build/run. Official Linux PowerShell archive SHA256 verified against its release hashes: `1fd7983fe56ca9e6233f126925edb24bf6b6b33e356b69996d925c4db94e2fef`. Initial host failed on read-only default cache; XDG cache/config/data overrides fixed it. `chdman help` returns 1 by design; setup now checks that status plus the actual banner rather than masking arbitrary errors. Full Linux setup/check script pair passed after correction.

Gate audit: qa_reviewer confirmed M0 Linux evidence PASS and three bootstrap tests passed; found missing Windows GLEW dependency (`sm64ex/Makefile:527`, `src/pc/gfx/gfx_opengl.c:19`). Added `mingw-w64-x86_64-glew`; read-only re-review confirms preparation by syntax/dependency inspection PASS. Native Windows compilation/run remains NOT_TESTED; original gameplay/fusion BLOCKED. No repeated upstream builds. Environment draft confirmed saved with install_script/start_skill; it still requires user review/save/publication, none of which is claimed executed.


## Native event adapter continuation — 2026-10-09

M0 `6e21f41` preserved and pushed to `origin/m0-recon` before further edits. No repeated Astra or source reconnaissance. New authored integration exports native coin count/position/counter after the existing SM64 interaction; Crash observes native catalog level and applies a guarded active-low controller pulse through the supported source-mod API. Engines/physics/renderers remain unchanged. [Contract](CONTRACT.md), [actual Linux outputs](evidence/integration-results.txt), Windows commands in [WINDOWS.md](WINDOWS.md).

`bash tools/check_integration.sh` completed with exit 0: prepares a private pinned sm64ex copy, compiles the actual modified `src/game/interaction.c` translation unit, verifies `nm -u` references `cm64_coin`, builds production C sender with warnings as errors, then runs the real upstream `ModCompiler`/event bus against PSMemory fixture. **14 checks passed, VERIFIED_SYNTHETIC**: C/UDP/native compiler/pad integration, deduplication, release, foreign session, expiration, unarmed/title/Start/physical-Cross gates, oversized datagram, sender exit, no swallowed listener exception, unload and unpaired default behavior. No ROM, native pickup or Crash simulation was executed. gGlobalTimer is not asserted equivalent to Crash logical ticks.

`python -m unittest discover -s tests -v`: 6 passed (3 existing static + 3 config-preservation cases). Source preparation exercised twice and refused a local authored-module edit without overwriting it. Original M0 source Git trees remain clean. 8 PowerShell ASTs parsed using the retained PowerShell 7.5.4 Linux host; Windows builds/run **NOT_TESTED**. Initial preparation matched a forward declaration instead of the native definition; narrowed to the pinned definition and made fresh preparation transactional. The Roslyn test project now imports SDK props after its local ignored output path, removing its initial MSBuild output-path warning.

Read-only qa_reviewer audit: no architecture/API blocker; found stale wording and Windows SocketError.MessageSize handling. Both corrected; oversized-packet regression added. Actual Windows pause/grounded/pose, background input, coin fidelity and jump/landing remain BLOCKED by absent local owned files and native execution. This is implemented event-adapter code, not a playable fusion. Apphost startup corrects upstream ProcessPath-derived mod/settings location. Configuration backups and edited-mod protection tested. No ROM/assets, generated engine source, binaries or synthetic disc data committed; no release packaging ahead of gameplay validation.

## 2026-10-09 — Windows 11 x64, local owned-data verification

All game data stayed in an ignored private cache / local Downloads; none was copied into Git. Source revision at start: `af01739`, then Windows script fixes through `fe9f334`. Tools: PowerShell 7.6.6, .NET SDK 10.0.401, MSYS2 MINGW64 GCC 16.2.0, GDB 18.1. Local software OpenGL fallback: Mesa 26.2.4 x64 with release-asset SHA-256 `351fc8c8b695878ffb3eaa044b3ead08672a48b1a045e3c3e3975811df0f6695`; only two app-local DLLs were staged and no system display driver changed.

- Native Windows Launcher `dotnet build ... -f net10.0-windows -p:PlatformTarget=x64`: PASS after deleting incorrect global `TargetFrameworks` override. `Test-Integration.ps1`: 14/14 PASS, **VERIFIED_SYNTHETIC**. Windows project unit tests: 6/6 PASS, **VERIFIED_SYNTHETIC**.
- Local Mario US data matched upstream expected SHA-1, and `sm64ex-cm64` built using explicit `WINDOWS_BUILD=1 HOST_OS=Windows`. Output `sm64.us.f3dex2e.exe`. Native default OpenGL startup exited with `0xC0000005`; GDB backtrace: null call inside `gfx_opengl_init`, then `gfx_init`, `main_func`, `SDL_main`. With application-local Mesa llvmpipe, the native Mario process created a window and remained alive and responsive for a 9-second test. **VERIFIED_REAL for process/window startup only; gameplay NOT_TESTED**.
- Crash USA local CUE points at BIN with MODE2/2352. Internal disc data contained the expected US identifier. The real Crash Launcher smoke read `SYSTEM.CNF`, processed the PS executable, generated its recompiled assembly and loaded `cm64-coin-jump`. Default GPU path reported `WGL: driver does not appear to support OpenGL`; the smoke command returned 0 anyway, showing its exit is **not** a valid graphics oracle. With private Mesa llvmpipe, the actual runtime logged `[Host] OpenGL window ready` and ran. **VERIFIED_REAL for disc recognition/bootstrap/window only; gameplay NOT_TESTED**.
- Real paired passive run: `Start-Integration.ps1 -CrashDisc <local-cue> -Seconds 45` without `-Apply`, with private software GL, produced two live/responding native Windows game windows and Crash's `[cm64] receiver ready ... apply=False`. Script exit 0, run JSON deliberately records gameplay/jump/landing/shared_world `NOT_TESTED`. No native coin pickup or cross-game event was observed. **VERIFIED_REAL for runtime process startup and receiver readiness, not actual shared gameplay**.
- Both game runtimes reported missing WASAPI audio endpoint during the remote test. Actual sound, visible gameplay fidelity, physics, coin effects, Crash jump and landing remain NOT_TESTED. Software GL may be slow and is only a test fallback.

The next precise test is a human-observed Mario yellow coin pickup, correlated to Crash's `received` log with distinct session sequence, followed by a guarded `-Apply` run and visual/native-state evidence of Crash jump and landing. Avoid inventing those results. See [WINDOWS.md](WINDOWS.md) and [STATUS.md](STATUS.md).

## 2026-10-09 — Native Mario coin received by native Crash on Windows

Session `20261009-142540-868`, real game runtimes, passive `Apply=False`: Mario recorded `coin seq=1` / `seq=2` at native ticks 6080/6081 and `coin seq=3` / `seq=4` at ticks 13483/13513. The live Crash runtime logged the corresponding `received seq=1..4` followed by `observe-only/drop` for every event. This is **VERIFIED_REAL for native coin observation and cross-runtime loopback receipt**, not for automated jump or shared-world rendering. Original game files and log transcripts remain local; no game data uploaded.

Keyboard-only enhancement `5aac846`: `-Apply -KeyboardArm` arms one Cross pulse for up to 60 seconds after pressing and releasing Crash R1 (default keyboard W), with single-use, Start, level-change, and expiry guards. Windows native fixture tests **21/21 PASS**, Python tests **6/6 PASS**, script AST **0 errors**. A live Windows run logged `keyboard_arm=True` and multiple `keyboard armed crash_level=9` events. **No live `input_applied`, actual Crash jump or landing verified yet.**

## Windows real native input application — 2026-10-09

The operator collected two SM64 coins in the real Windows apply-mode paired session 20261009-144206-583, with keyboard arm enabled and original/recompiled Crash running concurrently. Local ignored logs only; no game data in Git.

- Mario native stderr: coin seq=1 native_tick=17208 coins=1; coin seq=2 native_tick=17209 coins=2; both sent 52-byte native messages.
- Crash stdout: receiver ready port=53768 apply=True keyboard_arm=True; keyboard armed crash_level=9.
- Crash stdout: received seq=1 at crash_level=9, then input_applied seq=1; received seq=2 at crash_level=9, then observe-only/drop seq=2.

VERIFIED_REAL: Mario native pickup -> UDP event -> Crash native runtime reception -> guarded active-low controller Cross pulse, with one-shot arm honored. NOT_VERIFIED: Crash visually jumping/landing, grounded/velocity changes, shared-world simulation or camera. Input_applied does not prove an actual physical jump. Synthetic regression 21/21 and Python 6/6 passed for keyboard arm code. Next gate: observe and instrument Crash jump/landing during actual gameplay.

## 2026-10-09 — Post-input real-runtime motion probe prepared

The source mod now reads confirmed pinned Crash US-native player address/offsets (from upstream `RecompOne.Runtime/Host/FramePacing.cs`) only after the existing guarded Cross pulse. For at most 3.5 seconds it samples signed raw translation Y / vertical velocity, state, AIR and GROUNDLAND flags at ~120-ms intervals, then writes `motion_summary` with explicit `interpretation=OBSERVATION_ONLY`. No original game memory writes, renderer or physics changes. Invalid pointer, level change, pause and unload terminate sampling safely.

On Windows 11 with real upstream mod compiler and a fixture `PSMemory` player object, `Test-Integration.ps1` passed **25/25** checks (the previous 21 plus baseline read, simulated AIR-to-ground read, no mutation of position/status, and bounded shutdown). The scenario simulated raw Y 100000→106000→100000 with AIR and GROUNDLAND transitions, yielding `rise_and_landing_candidate=True` as a diagnostic. `python -m unittest discover -s tests -v` passed **6/6**. **Classification: VERIFIED_SYNTHETIC for motion instrumentation only.** Previously witnessed real `input_applied seq=1` remains VERIFIED_REAL as a controller event; native position change and actual jump/landing after it are **NOT_VERIFIED**, pending a new real paired run and visual review. Do not infer physical movement from the fixture.

## 2026-10-09 — VERIFIED_REAL: Crash native jump arc and landing after Mario coin

Paired Windows 11 x64 native game execution. Local private logs: `%LOCALAPPDATA%/CrashMarioFusion/M0/logs/20261009-151351-877`. Applied one-shot keyboard authorization (W/R1 in Crash, then Mario yellow-coin pickup). The actual original/recompiled Crash guest player object was observed read-only for 3.5 s by the native PadReadEvent source mod; this was **not fixture RAM**. The two original runtimes remained separate processes/windows.

- Mario stderr: `coin seq=1 native_tick=4520 coins=1 ... sent=52`; `coin seq=2 native_tick=4529 coins=2 ... sent=52`.
- Crash stdout: `keyboard armed crash_level=9`; `received seq=1 ... crash_level=9`; `input_applied seq=1`; `received seq=2 ... crash_level=9`; `observe-only/drop seq=2`.
- Native Crash motion `seq=1`: 22 samples. First raw Y `1387515`, max Y `1546674`, last Y `1387507` (near start); AIR flag `false → true → false`; GROUNDLAND flag `true → false → true`; rising velocity first positive (`939200`), then negative during falling (`-1100800`), then grounded. During flight, original state indexes changed `1 → 4 → 11 → 13 → 1` across the recorded sequence.
- Summary (as emitted by live game): `motion_summary seq=1 reason=window_complete samples=22 y_start=1387515 y_min=1387507 y_max=1546674 y_last=1387507 air_flag_seen=True ground_after_air=True rise_and_landing_candidate=True interpretation=OBSERVATION_ONLY`.

Classification: **VERIFIED_REAL** for native Mario coin pickup, sequence-matched IPC, guarded Cross pulse and native Crash physical upward movement/airborne-to-grounded transition temporally following the event. This is stronger than input-only evidence. However **causal exclusivity is not proven by one run** (a baseline/no-pulse comparison and visual operator confirmation remain useful). No unified physical world, collisions, camera, single renderer, or production-quality performance has been implemented or validated. Data remains in private logs; game binaries/data MUST NOT enter Git.

Next M2 gate: repeat with a passive/no-Apply control run while Crash stays idle to establish that no corresponding guest jump arc occurs; then one more Apply keyboard-arm run. Record video or visual confirmation if available, gameplay pause/death guards, and report exact source revisions. Only then plan the smallest shared-world collision/rendering prototype.

## 2026-10-09 — Human visual corroboration of native jump

After the instrumented real Windows run `20261009-151351-877`, the user explicitly confirmed in chat: they visually saw Crash jump at the same time as the Mario coin pickup. This is a **human eyewitness confirmation reported by the tester**, not a captured video, independent replay, or extra automated run. It corroborates the prior native trace of 22 samples, rising/falling Y, AIR true-to-false and GROUNDLAND re-established, correlated with `received seq=1` and `input_applied seq=1`.

**M2 real cross-game coin-to-jump demonstration: PASS, with native telemetry plus tester visual confirmation.** Precision of 'at the same time' is based on the user's perception, not measured cross-engine latency; do not claim zero latency or shared simulation ticks. A no-Apply control run is still advisable for causal isolation, but is not grounds to erase the confirmed interactive demonstration. Shared geometry, collisions, camera, single-world rendering and finished fusion remain UNIMPLEMENTED. Preserve commercial input files locally.

## 2026-10-09 — Asset-free Codex handoff test gate

Created `tests/fixtures/windows_coin_jump_20261009.json` (sanitized transcription of 22 original-runtime motion samples, no assets), `tests/test_recorded_windows_trace.py` (five fixture-consistency checks), `tests/test_native_sender_protocol.py` (one compiled production C CMJ1 UDP loopback check), `.github/workflows/source-only-checks.yml`, and `docs/CODEX_HANDOFF.md`.

On the authorized Windows 11 x64 machine, after a clean fast-forward to commit `e255f74`, ran `python -m unittest discover -s tests -v` with MSYS2 MINGW64 GCC available in PATH. **12/12 passed, exit 0, in 4.678 s**: three mod-installation unit checks, three project configuration checks, five historical-trace consistency checks, and one real C sender/local UDP test. `git diff --check` exit 0 and working tree clean. **Classification: VERIFIED_SYNTHETIC** for these new tests, because this run did not execute retail game runtimes; earlier native Windows M2 validation remains separately VERIFIED_REAL.

GitHub Actions workflow created for Python/GCC source-only CI, but its hosted-run status has not yet been confirmed in this evidence. No commercial file was committed. Cloud Codex must rerun tests independently in its environment and report that run's results, not attribute Windows results to Cloud.

## 2026-10-09 — GitHub hosted source-only CI confirmed

GitHub Actions **Asset-free integration checks** completed successfully on hosted Ubuntu, triggered by push to `m0-recon` at commit `9e052f0d7b71a7ec09cb88c477a1cdc96ded4bb6`.

- [Workflow run 37952281792](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37952281792): status `completed`, conclusion `success`.
- Job `Python tests and native C sender` (job id `113893843734`): conclusion `success`; `Checkout source only`, `Set up Python 3.12`, `Test source-only code, recorded trace, and live loopback C sender`, and `Explicitly report verification level` all individually report `success`.
- A separate local Windows invocation of the same source-only unit suite ran **12/12**, exit 0, with MSYS2 MINGW64 GCC available.

Classification: **VERIFIED_SYNTHETIC** on the hosted Linux runner, which executes the C sender and test fixture but does NOT launch original Crash/SM64 ROMs. No commercial assets or game files entered GitHub. The earlier Windows game-runtime jump telemetry remains a separate, operator-confirmed **VERIFIED_REAL** result. A future Codex Cloud session should run its own tests and report its own exit status.
## M3 coordinate increment — Cloud Linux, 2026-10-09

Base: `m0-recon` **38bb59413071995c921efd87bf95c8fd51d3e83b**;
working branch `feat/m3-coordinate-contract`. Read Issue #1 through GitHub HTML
(API blocked by proxy), canonical CODEX_HANDOFF and the relevant pinned source
seams. Existing Windows M2 observations are retained; no games ran in Cloud.

- `python -m unittest discover -s tests -v`: **17/17 PASS**, Python 3.12.14,
  GCC 14.2.0. Includes actual C UDP wire sender plus synthetic coordinate
  invariants, signed fixed-point extrema, f32 precision-collapse rejection,
  floor-boundary checks, source-level guards and recorded Windows trace replay.
- `bash tools/check_integration.sh`: **27 checks PASS**, .NET SDK 10.0.401.
  Compiled patched pinned sm64ex `interaction.c`, production C sender and
  Crash mod via actual upstream ModCompiler/event bus; player RAM is a fixture.
  Signed XYZ output and preservation of horizontal player fields asserted.
- PowerShell 7.5.4 AST parse of `tools/windows/*.ps1`: **9 PASS** on Linux,
  including Test-WorldCoordinates. This is not native Windows execution.
- `python tools/world_coordinates.py --log
  /workspace/.cache/crash-mario-m0/logs/integration-checks.log --calibration
  .cache/integration/synthetic-world-calibration.json`: **PASS**, two actual
  compiled-adapter fixture log samples consumed, inverse error 0. Test placement
  is explicitly SYNTHETIC_FIXTURE_ONLY, not a proposed native-game calibration.
  Reports/logs remain in ignored local caches. `git diff --check`: PASS.

All new results are **VERIFIED_SYNTHETIC**. Real Windows XYZ acquisition,
calibration, shared geometry/collision/rendering: **NOT_TESTED / NOT IMPLEMENTED**.
No commercial files, extracted resources or generated game binaries added.
QA review found possible float32 collapse with extreme calibrations; corrected
with per-sample half-raw-unit inverse-error rejection and regression cases.
No new Astra decision was necessary; D005 preserves the existing architecture.

Publication: implementation **210911e** pushed successfully to
`origin/feat/m3-coordinate-contract`. `gh pr create --base m0-recon --head
feat/m3-coordinate-contract` failed: `Post https://api.github.com/graphql:
Forbidden`; unauthenticated API CONNECT also returned HTTP 403 from Envoy.
The configuration lacked `api.github.com`; an additive allowed-domain draft
was saved (requires review/save and environment publication, not applied here).
PR creation and this branch's PR-triggered hosted CI remain BLOCKED.
Open manually at
https://github.com/kauankelvin7/crash-mario-fusion/compare/m0-recon...feat/m3-coordinate-contract?expand=1
or retry `gh pr create --repo kauankelvin7/crash-mario-fusion --base m0-recon
--head feat/m3-coordinate-contract` after supported API access works. No merge.

## M3 native Windows preflight — independent verification

The M3 branch `748443e` was checked out separately on the authorized Windows 11 host in a clean detached worktree; the existing local `m0-recon` checkout remained unchanged. Native tests on Windows: `python -m unittest discover -s tests -v` **17/17 PASS**, `tools/windows/Test-Integration.ps1` **27/27 PASS** using upstream compiled Crash adapter and fixture RAM, PowerShell AST syntax **9/9 PASS**. `tools/windows/Build-Integration.ps1` **exit 0** after private original-runtime build and installation; the M3 Crash mod source SHA-256 matched the installed source. The source/archive `git HEAD` warning is non-fatal; no runtime success is inferred from that warning.

`tools/windows/Test-WorldCoordinates.ps1` **exit 0** on two adapter-fixture samples with deliberate calibration `mario_frame=SYNTHETIC_FIXTURE_ONLY_NOT_PHYSICAL_ALIGNMENT` (scale 1, yaw 0), both roundtrip errors 0 and conservative floor range true. These anchors deliberately do **not** claim real-game spatial alignment. The calibration and all output remain in the private Windows cache. GitHub Actions pull-request [run 37955403614](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37955403614) succeeded on hosted Linux (source-only).

A fresh private paired real-game session was started with `-Apply -KeyboardArm`, native Crash receiver ready and both windows responsive. At the time of this record no native M3 XYZ sample had yet been collected; **Windows native XYZ movement/calibrated cross-game placement remain NOT_TESTED**. All listed test results are **VERIFIED_SYNTHETIC**, except original-run *startup* being VERIFIED_REAL for process/window readiness. The prior M2 live jump is separate and remains confirmed. PR [#2](https://github.com/kauankelvin7/crash-mario-fusion/pull/2) is open as a **draft** against `m0-recon`; this supersedes the earlier Codex proxy/PR-blocked note. No merge or retail data upload.

## Asset-free M3 geometry preflight — source review and CI

Read-only source inspection of pinned upstream sm64ex `d7ca2c0` found `struct Surface` holding signed `Vec3s` vertices in `include/types.h:228-243`, static/dynamic 16×16 partitions and per-cell surface-node fan-out in `src/engine/surface_load.c:24-25,266-294`, `find_floor` float-to-s16 casts in `src/engine/surface_collision.c:512-544`, and `alloc_surface_node`/`alloc_surface` increments with ineffective empty overrun guard bodies in `src/engine/surface_load.c:43-75`. Upstream active pool occupancy has **not** been measured; an arbitrary native insertion could overrun those pools.

Added `tools/geometry_preflight.py`, `tests/test_geometry_preflight.py`, and `docs/M3_GEOMETRY_GATE.md`. These accept **synthetic, caller-authored** triangle vertices already in Crash view units, require explicit frame/level mapping, check face indices, duplicate/degenerate geometry, winding, numeric bounds, float32 retention and **collapse or flipped orientation after native signed-s16 truncation**. Preview caps (4096 vertices, 512 triangles) are independent tool caps, explicitly **NOT proof of available native surface pool**. Output says no native collision, rendering, material or capacity verification has occurred.

Hosted GitHub Actions [run 37957543671](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37957543671) completed successfully against this source-only change; a prior run [37957367390](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37957367390) logs **25 Python tests PASS** including 8 geometry tests and the original C/UDP sender. This is **VERIFIED_SYNTHETIC only**, **NOT_TESTED** for collision/geometry in the actual Crash/SM64 runtime. No Windows games were launched during this source-only increment; native XYZ/operator calibration remain pending. 
## M3 original collision-code oracle and snapshots — Cloud, 2026-10-09

Continued remote feature at `a0abc0b36abac45d8d306b2a5a3ea81a4fa9fa47`;
native geometry implementation commit `469b421`. Did not repeat M0/M1/M2.
Read latest gate/handoff and attached existing draft PR #2 targeting m0-recon.

- `python -m unittest discover -s tests -v`: **34 PASS, exit 0**, no skips
  in this Cloud run. Python 3.12.14 / GCC 14.2.0; log ignored at
  `.cache/integration/m3-geometry-tests.log`.
- Native oracle compiles unchanged pinned full-sm64ex `surface_load.c` and
  `surface_collision.c`, using linker GC for unrelated code, Linux
  `-fsanitize=address,undefined -fno-sanitize-recover=all`. Six authored type/yaw
  cases verify mapped integer vertices, floor height 20, upward native normal,
  DEFAULT/BURNING type retention and signed room metadata, exact node fan-out,
  no-insertion control, capacity refusal with existing contact retained,
  time-stop retention and dynamic cleanup. No character simulation or burning
  gameplay tested. Malformed/truncated/oversized inputs rejected; no sanitizer
  findings. Pool sizes belong only to the fixture (2 surfaces/256 nodes).
- `bash tools/check_integration.sh`: **27 checks PASS, exit 0**, .NET 10.0.401;
  log `.cache/integration/m3-event-regression.log`. Original M2 C sender / native
  compiler / pad-event fixture regression remains passing.
- PowerShell 7.5.4 parser: **10 ASTs PASS**, including Test-Geometry.ps1,
  on Linux. New Windows script execution **NOT_TESTED**; no game launched.
- CMW1 deterministic tests: raw native pose/state types and packet lengths,
  malformed/nonfinite rejection, session/frame identity, ordering, pause and
  receiver-age expiry, independent native tick wrap, two-slot storage over
  2000 accepted observations. No live emitters or cross-clock freshness claim.
- Read-only gate QA: PASS. Fresh explicit gpt-6-astra architectural review
  returned conditional boundary-replica recommendation; evidence/limits in D006.
  Authoritative Crash collision volume units, guest query layout/material
  semantics and actual Mario pool availability are not inferred by this proof.

All new results **VERIFIED_SYNTHETIC**. Live native geometry/collision/rendering,
pose synchronization and gameplay **NOT_TESTED/UNIMPLEMENTED**. Original
commercial files and private Windows traces remain off Git; no remote PC used.
Hosted workflow now checks pinned public sm64ex and runs the native oracle;
explicitly configured missing sources/compiler fail rather than skip.

Published code commit **857a6a13260678ac9cdeda3d290320177821d3e8**; draft
[PR #2](https://github.com/kauankelvin7/crash-mario-fusion/pull/2) updated via
REST after the local gh editor hit the deprecated Projects-classic query.
[Hosted CI 37959761599](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37959761599)
conclusion **success**, with public-source checkout and test steps successful
according to the jobs API. Individual hosted logs could not be downloaded:
proxy denied `results-receiver.actions.githubusercontent.com`; exact test
counts above come from the Cloud-local log, not that unavailable archive.
No merge, remote Windows execution or release performed.

## M3 native Windows geometry oracle and source-only regression — 2026-10-09

On the user's connected Windows 11 machine, checked out exact feature commit `cbaa67a` in an isolated clean Git worktree (`crash-mario-fusion-m3`) without changing the original checkout or starting either game. First execution of `tools/windows/Test-Geometry.ps1` failed at MinGW/PE-COFF link time: unrelated full-game references from pinned `surface_load.c` and `surface_collision.c` were not eliminated by section GC as they were on Linux. The captured linker output included `main_pool_alloc`, object/terrain helpers, debug helpers, vector helpers and engine globals. This is a Windows test-harness portability issue, not evidence of an original-game collision failure.

Added Windows-only **fail-fast, unreachable dependency stubs** in `tests/native_geometry_probe.c` for unrelated full-game entry points. Any accidental call aborts the fixture rather than supplying simulated collision behavior. The original `read_surface_data`, `add_surface`, `find_floor`, partition and dynamic cleanup implementations remain compiled from the exact pinned upstream source. No game executable or upstream source was patched.

After the fix, `Test-Geometry.ps1`: **17/17 PASS, exit 0** (including 2 native original-code oracle tests); `Test-Integration.ps1`: **27/27 PASS, exit 0** (fixture RAM); complete MSYS2 Python source suite with `CM64_SM64EX_ROOT` pinned: **34/34 PASS, exit 0**, no skips. All **VERIFIED_SYNTHETIC on native Windows**, not real geometry/physics in the games. Original M2 real jump evidence is unchanged. Authentic M3 XYZ, operator-chosen calibration, source collider semantics, native pool occupancy, real collision injection and shared renderer remain NOT_TESTED or UNIMPLEMENTED. No commercial data was uploaded; no game was started. Keep PR #2 draft.

## M3 live Windows XYZ capture — 2026-10-09 (post-Windows oracle)
An authorized paired game session ran the private native Start-Integration.ps1 runner with Apply/KeyboardArm enabled on Windows. Both original game processes were alive and responsive when inspected. The private log remains under LOCALAPPDATA/CrashMarioFusion/M0/logs and MUST NOT be uploaded; only redacted conclusions follow.

The actual Crash receiver recorded two native Mario coin events (seq=1, seq=2) with distinct ticks/coin counts. The first was armed and recorded one native Cross application; the second did not record another input application. Real guest memory for seq=1 produced 22 motion samples, rising and falling native Y, 17 AIR samples, and grounded state after air movement with sustained GROUNDLAND. Native summary: rise_and_landing_candidate=True, classification OBSERVATION_ONLY. These data corroborate the M2 event-triggered jump. No new independent video was taken; do not claim a fresh visual confirmation.

This is a real signed XYZ/Crash-level read: all 22 native samples carried x_raw, y_raw, z_raw and crash_level=9. However X and Z each had ONLY ONE DISTINCT VALUE throughout the 3.5-second sampling window. Authentic native fields are observed, but varied horizontal movement and source units are NOT_VERIFIED. Mario level/area and separate landmarks were not observed, so cross-engine frame placement, scale and yaw remain UNCALIBRATED; Test-WorldCoordinates.ps1 was not run against a real calibrated pair. Neither original collision geometry nor native pool occupancy nor a collider insertion was tested.

Classification: VERIFIED_REAL for native coin receipt, signed XYZ field sampling and the recorded guest-memory rise/air/landing sequence. NOT_VERIFIED for horizontal movement, calibrated frame, geometry/collision equivalence or shared playable game. No local logs, game data or private artifacts were committed. PR stays draft.

## M3 second live Windows movement check — 2026-10-09
Same authorized native paired Windows session as previous entry, with additional user-directed gameplay. Inspecting both private Crash stdout and Mario stderr yielded four actual native Mario coin event emissions/receipts, sequences 1 through 4. Under explicit keyboard arming, only seq=1 and seq=3 logged input_applied; seq=2 and seq=4 explicitly logged observe-only/drop. Therefore 4 real receipts and 2 guarded original-game Cross applications. This documents gating behavior, not simultaneous shared-world collision.

For seq=1, the prior 22 samples showed Y rise/air/ground transition from player native X=2091776, Z=33844480. For seq=3, 20 additional genuine guest-memory XYZ samples also displayed Y rise, AIR and ground-after-air transition: initial X=1985280, Y=1086699, Z=31528192; final X=1987328, Z=31528192, with one in-window X change by +2048 native raw units after the air-to-ground transition. Comparing initial seq=1 vs seq=3: delta X=-106496, delta Z=-2316288 in native raw units. Three distinct XZ observations exist across the captures. This supports **VERIFIED_REAL varied horizontal coordinates across gameplay** and an X field change during active observation; no continuous walk trajectory or conversion of raw units to world metric units was proven. Crash level stayed 9 in all 42 samples.

The Mario native observer's stderr recorded the same four coin events with changing Mario XYZ (seq=1 to seq=4). These do not determine level/area identity or any shared landmark. Native calibration, relative axis/scale/yaw, Crash octree geometry provenance, original Mario pool occupancy, collider injection and shared rendering/gameplay remain NOT_VERIFIED or UNIMPLEMENTED. No new independent visual capture. Logs and ROM/disc assets remain locally private. PR is draft, no merge.

## M3.1 native Mario spatial observer: source, Windows build and synthetic QA — 2026-10-09
On the isolated Windows worktree, Codex CLI with explicit gpt-6-astra produced new opt-in CMW1 Mario pose emitter (integration/sm64/cm64_pose.[ch]), privacy-bounded loopback collector (tools/collect_pose.py), test fixture sender and protocol/source tests, plus private pinned-sm64ex generated-source hooks (tools/prepare_integration.py). Separate reviewer repaired Windows cp1252 default-decoding by making file reads/writes explicit UTF-8 in the source preparation workflow. The original pinned upstream Git checkout was untouched, and no game was launched for this M3.1 test. The existing CMJ1 coin behavior was left intact. Generated private runtime source under LOCALAPPDATA was updated by its existing source-preparation script, never uploaded.

Test commands from isolated worktree (MSYS2 MINGW64 Python, CM64_SM64EX_ROOT pointing to the clean pinned public sm64ex) yielded: python -m unittest tests.test_live_pose -v, **8/8 PASS**, including actual production C pose sender and native pinned game source compilation; python -m unittest discover -s tests -v, **42/42 PASS**. PowerShell 7 tools/windows/Test-Integration.ps1 yielded **27/27 PASS** (fixture RAM), and tools/windows/Test-Geometry.ps1 yielded **17/17 PASS** (original pinned collision code in fixture harness). tools/windows/Build-Integration.ps1 exited 0 on Windows: original Crash .NET Release built with 0 errors/0 warnings, private generated sm64ex updated and linked into the executable with both cm64_coin.o and **cm64_pose.o**. A non-fatal upstream Makefile git HEAD warning appeared in an archived non-Git source tree; make nevertheless completed successfully. The executable exists in the private cache, but **new native gameplay/pose packets NOT_TESTED**. Tests against faked clocks, source builds and synthetic geometry are VERIFIED_SYNTHETIC only; the live-game original M2 event/XYZ findings remain separately VERIFIED_REAL, not M3.1 evidence.

The CMW1 frame descriptor encodes native Mario level/area and an **observer epoch**, explicitly NOT the Mario engine's authoritative frame generation. Automatic world-coordinate calibration remains prohibited without real operator-chosen shared landmarks. Continuous Crash post-update capture was intentionally deferred: controller sampling is not established as a coherent physical tick. No collision ingestion or player memory write; no retail data or telemetry log in Git.

## M3.1 REAL Windows Mario continuous-pose validation — 2026-10-09 (supersedes new-pose NOT_TESTED)
After the successful native Mario Windows build at commit db30c5b, the user ran the documented opt-in private collector with the game during actual gameplay. Independently inspected private per-session JSONL and summary under LOCALAPPDATA/CrashMarioFusion/telemetry (NOT in Git): 1,137 accepted original-engine CMW1 Mario post-update packets, 0 rejected / 1,137 attempts, 1 current 16-byte session, contiguous sequences 1..1137, strictly increasing native ticks (468..4859) and receiver monotonic times, finite XYZ throughout; no paused=true frame was emitted. Elapsed time between first/last accepted packets 147.824 s of the 180-s bounded collector operation. Native level 16, native area 1 for the entire sampled run; observer-local generations 1..5, with sizes 480/57/84/252/264. These are NOT engine-authoritative generation IDs and do NOT prove an area change. All five frames corresponded to the same native level+area, so real area switching is still NOT_TESTED.

Distinct XYZ positions=441. Native player coordinate extents X [-3944.2393,6949.1470] (408 distinct X); Y [-1169.4817,1030.9401] (234 distinct Y); Z [-1683.9216,4778.2520] (399 distinct Z), all numeric units uncalibrated. 21 distinct native Mario action values, including the pinned-original labels ACT_WALKING=0x04000440, ACT_JUMP=0x03000880, ACT_DOUBLE_JUMP=0x03000881, ACT_TRIPLE_JUMP=0x01000882; this supports real walking/jumping observation. Never assume these native Mario coordinates are numerically aligned to Crash raw coordinates.

Arrival timing: overall 7.69 accepted packets/second during 147.824 s (including gaps); median interarrival approx 0.133 s; max observed count in any sliding 1-second arrival window 9 (<=10 Hz intended bound); source monotonic rate limiter independently covered by the previously green C tests. Four >0.5-s gaps observed near observer-epoch changes, of which the largest was 4.700 s, consistent with the operator's requested ~5-s pause. This absence of emitted records suggests gating, but is NOT direct proof of pause-button causality, because paused frames are intentionally never emitted; requires a time-marked manual pause control before claiming verified suppression. No native area transition was observed. The private mario.log has one SDL_OpenAudio WASAPI error (requested audio endpoint unavailable) but no telemetry failure; pose packets continued successfully. Collector's original machine summary deliberately says live_gameplay_verified=false / calibration_ready=false because the collector cannot itself perform independent visual certification; the separate evidence review verifies REAL native packets but makes NO new visual claim.

Classification: VERIFIED_REAL = native Mario CMW1 pose packets, valid XYZ changes, native original actions and level/area identity, delivery/sequence/frequency. PARTIALLY_OBSERVED = pause-like 4.7-s gap/observer invalidation. NOT_VERIFIED = actual area transition, visually verified pause gating, absolute world frame/time synchronization with Crash. NOT_IMPLEMENTED = continuous native Crash emitter or shared physics/geometry/rendering. Keep exact session identifier, session tokens, full JSONL, any private file contents and ROM out of Git; only aggregate conclusions are committed.

## M3.2 Crash diagnostic CMW1 observer — Windows implementation gate, 2026-10-09
In isolated source worktree feat/m3-local-validation, Codex CLI authored integration/crash_pose/CrashPoseMod.cs and mod.json, source-only private launcher preparation tools/prepare_crash_pose.py, tools/windows/Build-CrashPose.ps1 and Test-CrashPose.ps1, finite localhost-only tools/collect_crash_pose.py, Python tests/test_crash_pose.py and actual upstream mod fixture integration tests/crash_pose. Independent reviewer verified no replacement or change to pinned private original checkout, and repaired an idempotent private staging blocker by requiring a recognized pinned source and an incomplete/not-sealed private build before allowing resumption. No user game disc, ROM, retail files, telemetry JSONL, private full logs or tokens included in Git or uploaded.

Actual native seam: pinned RecompOne.Runtime.Events.PadReadEvent occurs during controller polling and is NOT verified as post-Crash-physics. Crash CMW1 phase=0 UNKNOWN_DIAGNOSTIC; observer callback ordinal, NOT simulated/native physics frame tick. The emitter reads pinned SCUS-94900 addresses from PSMemory.Ram direct read-only span to avoid IMemory.ReadU32 count-access/VBlank side effects, and tests confirm no RAM/input mutation. Signed native translation +0x80/+0x84/+0x88, signed native rotation +0x8c/+0x90/+0x94, state +0x2c and flags +0x120. Frame descriptor M32D+native level+observer epoch+reserved zero is an observer identity, NOT authentic physics generation. Calibration_ready is permanently false for this diagnostic workflow; original source geometry, collision insertion and cross-engine mapping remain NOT_VERIFIED.

Windows verification with MSYS2 MINGW64 Python, PowerShell 7, cached pinned public-source RecompOne launcher: python -m unittest tests.test_crash_pose -v passed 7/7; python -m unittest discover -s tests -v passed **49/49**; tools/windows/Test-CrashPose.ps1 passed **58/58 fixture assertions** with the actual pinned mod compiler, RAM implementation, native event bus, no memory writes, unchanged physical buttons and verified no access-counter/VBlank side effects; tools/windows/Test-Integration.ps1 passed **27/27**; tools/windows/Test-Geometry.ps1 passed **17/17**; tools/windows/Build-CrashPose.ps1 built separate private Win64 .NET launcher at LOCALAPPDATA/CrashMarioFusion/M3-crash-pose with **zero errors and warnings**, sealed allowlisted SHA-256 manifest; checked_launcher() verifies correct hash and only active diagnostic mod. No Crash game launched. All results VERIFIED_SYNTHETIC or Windows native build; runtime Crash M3.2 new packet collection is NOT_TESTED. Historical Mario 1,137 live pose and M2 42 Crash samples are separate evidence and cannot be substituted.

Next real gate: operator run the documented private 90–180s Crash collector, enter actual Crash level, walk and jump, pause/restart, then verify native X/Y/Z and signed rotations change coherently, scene level and observer epoch, rate<=10Hz, sequence and lifecycle, no input or physics change, and private-only logs. Do not proclaim coherent postphysics sampling from this experiment: require a real engine hook and independent correspondence landmarks before mapping two worlds. Never merge PR until authentic shared-world collision gate.
# Authored reference-box continuation — Cloud Linux

Base `a43ee9b` from latest `feat/m3-coordinate-contract`, new working branch
`feat/m3-reference-box`. First implementation commit `2dad120`.
No M0/M1/M2 restart, no games launched or commercial files downloaded.

- With `CM64_SM64EX_ROOT=/workspace/.cache/crash-mario-m0/sm64ex` and
  `CM64_C1_ROOT=/workspace/.cache/crash-mario-m0/c1`,
  `python -m unittest discover -s tests -v`: **54 PASS, no skips, exit 0**.
  Earlier baseline without explicit sm64ex root skipped one existing hook test;
  the configured final run executes it. Log `.cache/integration/m3-reference-tests.log`.
- Five new converter/native comparison tests execute exact pinned c1 query
  source slices and unchanged Mario loader/floor code, authored fixtures only.
  Source pins unchanged. Linux ASan/UBSan PASS, no findings. Single top:
  interior, diagonal, perimeter and outside responses match. Overlap: reference
  Crash **40**, Mario **48**, explicitly tested disagreement. Native query
  conventions differ; no gameplay or Launcher collision claimed.
- Fixed compact-coordinate domain: origin<=2047 for query-bound-zero;
  regressions reject origin2048 and origin3000 even with translated FrameMap.
  Query ABI assertions: record8 / descriptor16 / zone octree offset28 bytes.
- `dotnet run --project tests/crash_pose -p:CrashRoot=<pinned-public-cache>
  -- <repo>` with cached .NET10.0.401: **58 assertions PASS, exit0**.
  Log `.cache/integration/m3-crash-pose-regression.log`.
- `bash tools/check_integration.sh`: **27 checks PASS, exit0**, log
  `.cache/integration/m3-reference-event-regression.log`.
- PowerShell7.5.4/Linux parser: **13 ASTs PASS**, including new source-only
  Test-ReferenceGeometry.ps1. Workflow YAML parsed and steps validated.
- QA approved bounded authored proof after compact-domain correction.

All new results **VERIFIED_SYNTHETIC**. New Windows script **NOT_TESTED**;
real Crash pose/graphics/post-physics/geometry/capacity gates remain dependent
on the new computer. No state/input writes or physics replacements implemented.

Published commits `2dad120` and `1571f25`; [draft PR #4](https://github.com/kauankelvin7/crash-mario-fusion/pull/4)
targets **feat/m3-coordinate-contract**, verified through GitHub API.
[Hosted CI 37987762871](https://github.com/kauankelvin7/crash-mario-fusion/actions/runs/37987762871)
completed **success** for `1571f254c6803bb45e6962eace5dc5677cdc79d5`.
No merge or original-game execution performed.

## Issue #5 P1/P2 — executed Cloud checks, 2026-10-09
Environment: Linux Codex Cloud; existing branch `feat/m3-offline-preflight`,
checkpoint a43ee9b. Public sm64ex unchanged pin
`d7ca2c04364a6dd0dac58b47151e04e26887e6f0`; no retail files or game execution.

- P1 commit c6ff961: full suite **55 PASS** (six new observational tests);
  CMW1 single-session regression preserved, independent sessions/tick wraps,
  bounded two-slot memory, clocks, replay, phase, pause/rebind, frame, age/gap.
- P2 commit bb2eaed: `CM64_SM64EX_ROOT=/workspace/.cache/crash-mario-m0/sm64ex
  python -m unittest discover -s tests -v` — **65 PASS**, no skipped tests.
  Includes production C loopback senders and original public collision source
  in an isolated fixture oracle with Linux ASan/UBSan; no live native collider.
- `dotnet run --project tests/crash_pose/CrashPoseChecks.csproj
  -p:CrashRoot=/workspace/.cache/crash-mario-m0/CrashBandicoot-Launcher --
  /workspace/crash-mario-fusion` using cached .NET 10.0.401 (private writable
  DOTNET_CLI_HOME/NUGET_PACKAGES): **58 PASS** observer fixture assertions,
  unchanged RAM/inputs; `bash tools/check_integration.sh`: **27 PASS** M2 fixtures.
- `python -m tools.estimate_calibration --input
  tests/fixtures/calibration_landmarks_synthetic.json`: scale=2, yaw=90°,
  fit 3 / holdout 2, max/RMS residual=0 for both; maximum float32 fit error
  1.4210854715202004e-14 Mario unit and inverse error 7.105427357601002e-15
  Crash unit. **SYNTHETIC_MATH_ESTIMATE_ONLY**, not an inferred real-world map.
- PowerShell 7.5.4 AST parser on Linux: **13/13 PASS**, including the new
  Test-OfflinePreflight.ps1. Native Windows execution **NOT_TESTED**.
- Independent read-only `qa_reviewer`: **16/16 focused tests PASS**, no blocking
  defect in observational/math scope. No Astra invocation was needed; existing
  architecture preserved. `git diff --check`: PASS.

All new checks are **VERIFIED_SYNTHETIC**; prior Windows VERIFIED_REAL evidence
above remains historical and is not a new run. Local transient logs stay outside
Git. Runtime frame/landmark provenance, true Crash postphysics ownership, pause
causality/area transitions and shared gameplay remain **BLOCKED** pending an
operator-controlled Windows experiment on the new PC.
