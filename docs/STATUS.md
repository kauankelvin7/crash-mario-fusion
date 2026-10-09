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
