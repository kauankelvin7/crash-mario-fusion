# Engineering decisions

## D000: Preserve original gameplay; do not assume a winning implementation route

Status: ACCEPTED as project goal, not an implementation claim.

Candidates to investigate: dual-runtime passthrough, embedded/native library, hybrid. Record actual source revisions and probes before choosing.

## D001: Escalate hard architecture decisions to Astra

Status: explicit runtime Astra selection exercised in M0; automatic TOML routing NOT_TESTED.

Root: GPT-6.1 Sol Medium. Specialists: GPT-6 Astra High only for architecture/deep-debug gates. Codex Cloud may not honor project-scoped custom-agent model pinning; verify or request a separate supported Astra task.

## D002: Observe complete runtimes before committing to a bridge

Status: CONDITIONAL, Astra-reviewed on 2026-10-09. Real behavior NOT_TESTED. Pins/commands: [EVIDENCE.md](EVIDENCE.md).

Prefer CrashBandicoot-Launcher plus full sm64ex for the next observation probe. `GameLoader.Run` executes generated `Recompiled.Entry.Run`; sm64ex `produce_one_frame` invokes `game_loop_one_iteration`, retaining object/script/HUD/warp processing. Separate processes provide a reversible initial boundary; transport and synchronization remain undecided.

Compared alternatives: Crash + embedded libsm64 has a tested C boundary but libsm64 maps coins/stars/keys/doors/warps to `interact_noop`, failing the full-behavior requirement. Embedding two complete engines remains conceivable but adds unproven lifecycle/global-state coupling. c1 offers GOOL semantics but reports incomplete functionality; use it as a reference, not a fidelity-equivalent replacement. No neutral replacement physics or fresh engines are justified.

Astra gate: observe native SM64 yellow-coin pickup (`interact_coin`, `bhv_coin_sparkles_init`), requiring identical coin/healing/deletion consequences between baseline and passive instrumentation, plus exactly one event record. Identify Crash's actual object-update boundary separately from host `PresentFrame`. `HookManager.WrapIfHooked` excludes direct recompiler calls: hooks existing does not prove interception. Abort if these seams cannot be observed without changing gameplay.

Proposed first REAL cross-runtime M2 event: one native SM64 yellow-coin pickup requests one native Crash jump through mutable `PadReadEvent.Buttons` (`RecompOne.Runtime/Events/PadInput.cs::Filter`; upstream `examples/mods/auto-spin/AutoSpinMod.cs` demonstrates button filtering). This is a proposal, not implemented. M1 must confirm native jump mapping, one-edge press/release, deduplication, logical ticks and pause/load handling. Each engine owns its consequences. Oracle: one coin pickup/deletion and exactly one native Crash ground→jump→landing transition; baseline comparison; no repeats on replay/reconnect. This proves one event, not shared-world collision.

D001 runtime update: explicit `gpt-6-astra` override accepted by the available delegation tool and architecture verdict returned once. Project TOML auto-loading/root selection and separate resolved-model telemetry remain unverified; no silent Sol substitution occurred. Root did not infer its model from config files. Missing native observations keep D002 conditional; next work is M1 observation/contract, not IPC construction.

## D003: Windows x64 primary, Cloud Linux for development

ACCEPTED by user direction. Preserve D002. Crash uses upstream .NET/WinForms/OpenGL; sm64ex uses its existing MinGW x64/SDL2/OpenGL backend; libsm64 uses GNU Make/MinGW. No renderer replacement or new Astra call. PowerShell local workflow is prepared; native Windows compilation/execution remains NOT_TESTED.
