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

## D004: Implement the proposed narrow event without changing runtime architecture

Native sm64ex coin observer + Crash's supported source-mod/pad bus, loopback CMJ1 datagram, default observe-only with explicit R1-gated apply. Original engines retain consequences; no neutral physics or position injection. Actual adapters compiled/tested against the pinned code/APIs, but real gameplay remains BLOCKED. No repeat Astra review. Native Windows apphost replaces `dotnet.exe DLL` startup because upstream `AppPaths.Root` follows ProcessPath; this keeps mods/settings beside the launcher instead of the SDK. Final ZIP/Actions/Release packaging waits for real playable Windows validation and release authorization.
# D005 — M3 read-only calibrated coordinate path (2026-10-09)

Compare two next steps: (1) map native observations with explicit placement,
or (2) inject cross-game triangles into sm64ex's native surface loader. Route 2
would immediately require verified Crash geometry/materials, winding, local
frame identity and ownership of moving surfaces; none is supplied by the M2
position trace. Choose route 1 first: add signed XYZ reads to the existing
native observer and a tested reversible map with float32 precision and native
query-bounds guards. This is directly reusable before native surface loading;
it neither chooses the final world owner nor replaces either physics engine.
No new Astra review: no irreversible integration architecture is selected.
Next material decision remains which native world owns a shared collision
slice, after private Windows XYZ/calibration and native geometry evidence.

## D006 — Native collision oracle and conditional boundary replicas

New evidence: c1 `256fdcef` `ZoneQueryOctreeR`/`FindFloorY` (`src/solid.c`)
uses volumetric leaf AABBs and can average support heights; `ProcessNode`
type/subtype drives Crash events. Screen triangles/player coordinates do not
establish collision units or Mario material equivalence. Launcher `224da775`
already has physics/bound hooks, but guest query layout/lifetime is unverified.

Explicit specialist call: `/root/astra_m3_geometry`, selected through
`spawn_agent(model="gpt-6-astra", reasoning_effort="high", fork_turns="none")`;
tool accepted selection and returned review (no separate model telemetry).
Compared (A) validated static volume boundaries replicated into native Mario
surfaces, each solver retaining character authority, with (B) foreign Crash
floor queries inside Mario. Conditional recommendation A: B mixes support,
wall/ceiling/action semantics without a demonstrated compatible solver seam.
A also cannot generally reproduce Crash's averaged floors or event semantics.
Neither live world ownership nor fidelity equivalence is established.

Implemented next proof: authored triangles transformed by existing FrameMap,
explicit synthetic DEFAULT/BURNING type and room, exact cell fan-out and pool
reservation, then original full-sm64ex loader/`find_floor` in isolated pools.
No libsm64 substitution, game hook or live insertion. Original dynamic cleanup
and time-stop behavior are exercised; insufficient capacity fails before
allocation. Linux ASan/UBSan checks memory and arithmetic in this fixture only.
Real insertion still requires the gate's measured pool occupancy, atomic
reservation/lifecycle and authentic geometry/frame/material evidence.
Next source-only extension: one authored ordinary octree box against c1 and
Mario reference queries, including boundary/diagonal/outside cases and overlap
counterexamples. Live Crash extraction remains blocked by guest layout and
private Windows observations; do not infer volume units from player XYZ.
