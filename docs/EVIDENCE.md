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
