# Execution status

Date: 2026-10-09. Branch: `m0-recon`. Project base: `d45ffef659f606a779e158275e098947ba2ecd7c`.

- M0 reconnaissance: completed; six pinned upstream sources inspected. See [EVIDENCE.md](EVIDENCE.md).
- Architecture: CONDITIONAL, Astra-reviewed D002; favor complete Crash Launcher + sm64ex for passive observation. No transport selected or implemented.
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
- Synthetic cross-runtime event: NOT_TESTED; collision probe exercises one library, not a bridge.
- c1 full build: BLOCKED by missing GNU/i386 headers/dependencies; optional reference candidate. Assetless boot is unsafe because its stream reader assumes a valid file.
- Environment reproduction: `bash tools/m0-setup.sh`, then `bash tools/m0-check.sh`; retained sources/dependencies under `/workspace/.cache/crash-mario-m0`. Draft persistence/publication is separate from runtime validation.

Next: M1 passive native-event/tick observation and ownership contract, on a lawful test machine with owned data. Compare instrumented/uninstrumented SM64 coin pickup; identify Crash logical update/input seam across pause/loading. No fusion or gameplay fidelity is claimed.

Primary target: Windows 10/11 x64. Native Windows builds/gameplay: NOT_TESTED (no Windows runner here). Five PowerShell scripts provide setup/build/test/start; AST parsing on PowerShell 7.5.4/Linux and non-Windows platform guard passed. See [WINDOWS.md](WINDOWS.md). Linux results remain cloud-only.

QA gate: M0 Linux evidence PASS; Windows preparation by syntax/dependency inspection PASS after adding GLEW. Windows native build/run NOT_TESTED; original gameplay/fusion BLOCKED. Saved install_script/start_skill draft confirmed; publication and new-task restoration NOT_TESTED.
