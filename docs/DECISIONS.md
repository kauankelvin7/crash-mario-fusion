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

## D007 (2026-10-09): Diagnostic Crash pad-polling pose is not postphysics
Decision: implement the first Crash continuous CMW1 read-only observer via the separately-loaded pinned RecompOne PadReadEvent adapter, with phase=0 UNKNOWN_DIAGNOSTIC, native raw signed XYZ/rotation/level and explicit observer-only epoch/callback ordinal, never mislabel that callback as native physics completion or share-world calibration proof. Reason: available pinned launcher source does not establish a guaranteed callback after native Crash physics; editing upstream core or fabricating a POST_CRASH_PHYSICS contract would make evidence misleading. The private observer reads a direct RAM span to avoid PSMemory.ReadU32 runtime count-access/VBlank catchup; source-only fixture validates byte-identical RAM and input, 58 assertions. Built isolated private launcher instead of changing pinned original M0 or commercial assets. Alternate routes: implement source-proven real Crash physics-final hook in a reversible generated overlay later, or certify a strictly bounded pre-GPU seam with lifecycle evidence; both BLOCKED until native source/time ordering is independently demonstrated. Do not inject colliders or align coordinate spaces until actual real shared landmarks and verified native postphysics capture.
# D006 follow-up — measured boundary limitation

The existing conditional review is now exercised with an authored single-leaf
reference box, exact c1 query functions and full-sm64ex native surfaces.
Isolated top/perimeter cases agree; overlapping tops produce c1 40 vs Mario 48.
Retain native solver ownership and source volume metadata. Do not generalize
triangle replicas as equivalent Crash collision or infer retail material IDs.
No repeated Astra review or live architecture change. Source-coordinate compact
overflow is rejected before transformation, including compensated FrameMaps.

## D008 (2026-10-09): M3.3 passive receipt and scoped offline composition
Consolidate PR #4/#6 unchanged heads into a separate integration branch. Receive
both CMW1 emitters on one localhost socket with one receiver monotonic clock,
independent sessions/descriptors, fixed counters and finite private output.
No sender launch, inferred latency, native-tick alignment or auto-rebind. Preserve
P1 physical gates and original native solvers. Passing an estimated FrameMap
alone drops identity metadata, so the optional P2→authored-P3 composition checks
complete observer scope and synthetic provenance, then reuses existing native
numeric/material/capacity preflight. Operator estimates do not authorize real
geometry. No new engine architectural decision or equivalent Astra review needed.

## D007: Embedded native libsm64 as a reversible Mario-character slice (2026-10-09)

**Status: ACCEPTED AS EXPERIMENT, NOT FINAL FULL-FIDELITY ARCHITECTURE.** Evidence-backed alternatives are the existing full-sm64ex + Crash passthrough (M2 coin→jump VERIFIED_REAL; M3.7 paired receiver VERIFIED_REAL) versus a minimal Mario-character solver from pinned libsm64 hosted within Crash. Source review confirms libsm64 provides Mario physics, geometry buffers, imported texture data and static/dynamic surface functions; it also maps many original SM64 interactions to `interact_noop`. Codex CLI read-only review on the authorized Windows PC concurred with a bounded native-host diagnostic and cautioned about single-thread global state, guest rendering and collision provenance.

Implementation M4.0: C#/.NET 10 Cdecl ABI smoke, native Windows x64 `sm64.dll`, only one explicitly opted-in source mod on a separate copy of the original Crash Launcher. Actual Windows original-game session logged `INIT_OK` and `HOST_SOLVER frames=180 mesh_frames=180 moving_frames=101` with a responsive Crash window; privately owned and hash-pinned Mario ROM loaded in memory, no files published. A second bounded scripted run also PASS. This proves same-process guest solver invocation/CPU geometry generation ONLY. Do not infer co-rendering, Mario coin/warp semantics, authentic Crash surfaces or shared collisions from synthetic floor physics. Host VSync is a callback timing source, not proven native Crash postphysics.

Next decision/test: introduce a reviewed guest render pass to the Crash host while preserving original guest OpenGL state/depth and renderer lifetime; separately measure actual Crash collision volumes and re-evaluate frame ownership before authorizing mapped Mario collision. Preserve the full-sm64ex route until full original behavior equivalence becomes demonstrable. No merge to `main` or release.

## D008 — Use existing guest render callback for isolated original-Mario mesh preview (2026-10-09)

Selected a reversible **M4.1A diagnostic** via pinned public `MenuRegistry.RegisterWindow` (rendered in `HostWindow.OnRender`) rather than prematurely patching Crash's GL program, misusing VSync as GL callback, or replacing guest geometry with stock artwork. The Mario's original libsm64 CPU mesh positions/colors are defensively copied to immutable snapshots, clipped and depth-sorted in an independent ImGui window. Actual original Crash Windows capture visibly shows the guest character, and console confirms 752 original guest triangles drawn. This verifies guest visibility and lifecycle within the same host renderer **only**; no shared camera/depth, real Crash collider or full-SM64 object behavior. Next M4.1B needs dedicated host-managed FBO/texture/GL state preservation, scene-specific camera and transparent occlusion contract. Existing `MenuRegistry` has no unregister; persistent hot-reload semantics require extension before production. Maintain original gameplay unchanged.

## D009 — Exact original Crash OutputPanel image rectangle for M4.1B1 (2026-10-09)

Accepted an **intermediate, strictly diagnostic SCREEN-SPACE** on-image overlay: privately recompile only pinned public Crash host `RecompOne.Runtime.dll`, adding a duplicate-checked, lock-protected, unregisterable `MenuRegistry.RegisterOutputOverlay`, dispatch immediately after `OutputPanel.ImGui.Image` using `GetItemRectMin/Max`. Reuse immutable original Mario libsm64 guest triangles/color buffers and host ImGui clipped draw list. No new GL-state or framebuffer mutation, no guest pad/physics changes, commercial assets remain private. Read-only Codex local architecture review approved this for M4.1B1 **but not full M4.1B**. Original Windows screenshot verifies Mario over original Crash title and Sanity Beach island map; native guest ticks advanced 7→120 and Crash remained responsive. The overlay uses authored 2D anchor rather than verified world camera/occlusion and no genuine Crash volumes. Before gameplay gate, separately implement reviewed textured guest GL/FBO and real camera/depth/physics provenance. Do not merge main or claim shared world.
