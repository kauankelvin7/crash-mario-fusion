# Issue #19: G1 original world/GTE/OT source increment

2026-10-10, branch `feat/m42-world-source-gate`, base
`603baf2a47128ee2bafa9a34aeb8c3d8606029ad` plus this reviewed increment.
**VERIFIED_SYNTHETIC on native Windows; original-game attempt produced no G1 receipts.**
G1 is not accepted as VERIFIED_REAL and issue #19 remains open. No new overlay,
images, guest controls, native collision, depth pass or physical interaction.

## Independent review and bounded original attempt (supersedes initial proof below)

The reviewed schema **2** additionally rechecks the zone entry magic, its original
header pointer, world count and the raw polygon-ID word through successful guest
call completion. It exports the ID address/word and count so the independent
auditor verifies both halfword lanes and rejects out-of-range world identities.
Both probe and auditor reject a primitive overlapping any part of the OT.
The preparer checks clean exact pins for Launcher, c1 and libsm64, including in
check-only mode. Existing private clones are preserved; reviewed source is in
`.cache/m42-g1/world-source-reviewed`, never the original checkout.

Native Windows build: **3 positive fixtures**, original G3, rotated/translated
G3 and semitransparent GT3; **20 negative/opt-out cases** including zone-header,
zone-magic, world-count and polygon-ID drift. All hooks preserve RAM/scratch/GTE
state; accepted triangles have **0 integer pixel / 0 Z error**. The rebuilt
runtime has SHA256 `d153567ea353073bdf29af55ff58e366d053b6f164e3e763fdfc8b6aae7d3d1f`.
Six existing upstream warnings occurred on its clean build, no build errors.
All PowerShell scripts parse. Full source/native reference suite passes; see
the final counts in `docs/STATUS.md` rather than historical counts below.

`Run-WorldSourceProbe.ps1` verifies the sealed original host and prepared guest
DLL, creates a fresh private app under this worktree, and changes only that
app's runtime/configuration. No disc or ROM is copied. The retained prepared DLL
is byte-identical to its private manifest source; a stale manifest path is rebound
only in the new app. Mods, embedded Mario and authored overlay are **off** for
this observational G1 test. No keys are sent and no foreground checks bypassed.

The **60-second original Windows attempt** used own PID **1100**, remained
responsive, had empty stderr and was stopped; a subsequent process query
confirmed STOPPED. Private evidence is under
`.cache/m42-g1/original-e64d64c7f0994692a15f6f964c20c238/`.
There are **zero `[cm64-world]` receipts** in the native log: in-level source
capture was not established. No scene identity or native G1 acceptance is inferred
from boot/catalog messages. The first audit also encountered OEM-encoded unrelated
host noise; the auditor now ignores only non-probe noise bytes while keeping
probe lines strictly UTF-8, bounded and fail-closed. This log still fails with
`No source-owned original RTPT/OT receipts`; it is not relabeled as a fresh run.

Safe replay, PowerShell 7 executable (use the operator's existing private disc):

```powershell
& "$env:LOCALAPPDATA/Microsoft/WindowsApps/pwsh.exe" -NoProfile -File tools/windows/Build-WorldSourceProbe.ps1
& "$env:LOCALAPPDATA/Microsoft/WindowsApps/pwsh.exe" -NoProfile -File tools/windows/Test-ReferenceGeometry.ps1 -FullSuite -LogRoot .cache/m42-g1/review-reference-logs
& "$env:LOCALAPPDATA/Microsoft/WindowsApps/pwsh.exe" -NoProfile -File tools/windows/Run-WorldSourceProbe.ps1 -CrashDisc 'PRIVATE_OWNED_DISC.cue' -CheckOnly
& "$env:LOCALAPPDATA/Microsoft/WindowsApps/pwsh.exe" -NoProfile -File tools/windows/Run-WorldSourceProbe.ps1 -CrashDisc 'PRIVATE_OWNED_DISC.cue' -Seconds 60
```

An operator must enter actual normal-shader Sanity Beach during the bounded run
and verify the scene before accepting G1. Automated input is not guessed.
**G1 remains BLOCKED; G2 full native mesh/centre depth, G3 authentic contact,
G4 independent gameplay/restarts, G5 one real shared object, G6 end-to-end
reliability plus Linux/Windows CI remain unpassed.** G7 privacy safeguards are
maintained, but all seven gates are required before calling this playable.
No safe G2/G3 gameplay proof follows from a render triangle or a receipt-free run.

## Source trace and ownership

Read-only original public sources inspected at their exact pins:
- Crash Launcher `224da7757920a817de2d9242416f657ab95782ea`.
- c1 `256fdcef59f15a190290cc19db3fa9a707843b69`.
Both original checkouts remained clean. Current Universal Modder mashup skill,
mashup cases, bridge ownership and oracle references were consulted. Existing
libsm64 embedding is retained; this increment does not reopen architecture.

The trustworthy seam is **not PadRead, VSync or a host-wide float projection**:
- c1 `src/main.c:244` prepares the camera and dispatches the world shader;
  `GoolUpdateObjects` follows world rendering. This is not postphysics.
- `src/gfx.c:1522`, `GfxTransformWorlds`, original address `0x80019508`,
  loads `ms_cam_rot` and copies the eight 64-byte world descriptors to scratchpad.
- `src/psx/r3000a.s:2365`, `RGteTransformWorlds`, iterates packed poly IDs.
  At its `cop2 0x280030`, T4 is world index, S7/T8 are polygon/vertex bases,
  T2+2 identifies the current poly ID and T3 is the pending primitive.
  The two polygon words select three eight-byte packed WGEO vertices; their
  exact bit masks populate GTE VXY/VZ0..2 before RTPT.
- The same routine writes SXY12/13/14 into G3 or GT3 packet words and links
  those packets into the original 2048-word OT. GTE SZ17/18/19 belong to those
  three RTPT inputs, not to a screen-coordinate cache match.
- Launcher `RecompOne.Recompiler/CodeGen/InstructionEmitter.cs:124` emits
  original COP2 commands through `Gte.Execute`; registers remain on CpuContext.
  `Dispatch/Dispatcher.cs:183` owns function calls, `Hardware/Gte.cs:224`
  owns integer RTPT, and `Memory/Dma.cs:126` owns OT clear/build generation.

Camera/render preparation is independently checked against raw RAM:
GTE rotation must equal `ms_cam_rot` at `0x800577E4`; raw `cam_trans`
is at `0x80057864`. `GfxLoadWorlds` in `gfx.c:1484` establishes
`TR = (ms_cam_rot * (world_origin - (cam_trans >> 8))) >> 12`.
The auditor checks that integer relation, not a guessed pure rotation matrix.
Scope addresses `cur_zone/cur_path/draw_count` are grounded in
`c1/src/level.c:20` and `level.c:30`.
The descriptor's first word is exported as **world_key**, not an immutable EID:
`NSLookup` at `src/ns.c:1243` can replace that union word with a PTE reference.

## Implemented bounded capture

`integration/embedded_mario/CrashWorldSourceProbe.cs` is compiled into a new
repo-local derivative runtime; `CM64_WORLD_SOURCE_PROBE=1` opts in. It has no
mod/event registration, network channel, guest RAM writes or GPU calls.
Only plain `GfxTransformWorlds` is supported; fog/ripple/dark variants are
deliberately not inferred from the normal assembly register layout.

Before one original RTPT per eligible world call, it checks live gameplay,
pause, the OT base against the preceding DMA clear, RAM bounds and zone entry;
matches loaded zone descriptors to scratchpad; checks header counts/backdrop,
poly ID and source indices; compares decoded source XYZ with all three GTE inputs;
copies raw controls, camera and source words. Immediately after that RTPT it
captures SXY/Z/FLAG. At successful guest function completion it rechecks scene,
draw serial, camera and immutable source words, packet SXY, G3/GT3 code and
a bounded original OT link chain. Failed guest calls cannot emit a receipt.

Limits: **24 receipts, 90 seconds from first hook use, >=900 ms between attempts**;
at most 8192 OT-link reads and 128 links in a returned chain. Saturation,
missing source identity, unsupported shaders and stale/reset scopes produce no
accepted receipt. Exceptions stop the probe without changing guest exceptions.
`ot_generation` is this observer's serial of actual DMA clears; `epoch` is a
diagnostic scene/continuity epoch, **not an allocator/object generation**.
`draw` is the original render-build counter, not a certified physics frame.

`tools/assess_world_source_probe.py` streams bounded private UTF-8 stdout,
rejects malformed/duplicate fields, invalid types/spans, mixed scene epochs,
stale OT generations, degenerate or unidentified triangles and broken OT links.
It independently implements the pinned runtime's integer UNR reciprocal,
matrix/translation, truncation and packed SXY projection. Supported receipts
must have **zero integer pixel and Z reprojection error**; failures report
per-vertex dx/dy/Z error. Saturation/overflow are rejected, not approximated.
It never authenticates a log as a game run and never enables depth/collision.

## Native Windows proofs (initial implementation)

Commands executed with all intentional build/log/temp outputs inside this repo:
`pwsh -NoProfile -File tools/windows/Build-WorldSourceProbe.ps1`
and `pwsh -NoProfile -File tools/windows/Test-ReferenceGeometry.ps1 -FullSuite -LogRoot .cache/m42-g1/reference-logs`.
PowerShell **7.6.6**, .NET SDK **10.0.401**, MinGW Python **3.14.5**, GCC **16.1.0**.

- Private original-source runtime compiled, **0 errors**. Its first clean build
  reported six existing upstream warnings; no new probe warning was reported.
- Two asset-free compiled fixtures execute the **actual pinned upstream Gte.cs**:
  identity and nontrivial rotation/world-camera translation/non-power-of-two
  projection. Both audit three distinct vertices with **0 px / 0 Z error**.
  Memory and GTE registers are compared before/after every probe hook.
- **16 native negative/opt-out checks** pass: missing/wrong OT, pause, unsupported
  call, scratch/vertex mismatch, actual divide saturation, frame/zone/camera
  drift, missing OT link, wrong SXY, OT reset, guest failure, wrong matrix, opt-out.
- **156/156 FullSuite tests pass, zero skips**, including original c1/sm64ex
  native source/reference oracles and 16 new parser/adaptation test methods.

Ignored evidence: `.cache/m42-g1/build-evidence.json`, `fixture.log`,
`fixture-rotated.log`, and
`.cache/m42-g1/reference-logs/20261010-110650-450/reference-box-checks.log`.
The build manifest records source/probe/runtime hashes; the final native runtime
SHA256 is `e85d46f7f98daa5ce699683487e7debeb82dae17dc162ad4bf578ad6ad5c2c1c`.
Initial fixture corruption tests touched non-geometry bits and were corrected;
an indentation error and a fixture FLAG-write assumption were also corrected.
The final build, native fixtures and complete suite all pass; no failure is hidden.

The first SDK invocation printed development-certificate initialization.
The build now explicitly disables that .NET first-run action; no game/source
checkout was changed. Original Mario texture/UV/GL-owner sources are unchanged
and exactly verified in the derivative, not replaced or simplified.
The configured `crash_recon` delegation failed on unavailable model
`gpt-6.1-sol`; no specialist or independent QA run is claimed. The orchestration
assistant must independently review this increment before accepting a gate.

## Initial handoff, and collision seam

1. Operator prepares a **separate sealed app inside this repo's ignored cache**
   from the previously verified textured baseline, retaining original executable,
   Crash DLL, libsm64 DLL and complete mod sources/owned-game path configuration.
   Install only the newly compiled derivative runtime from
   `.cache/m42-g1/runtime/RecompOne.Runtime.dll`; never replace an original app.
2. Enable `CM64_WORLD_SOURCE_PROBE=1` and the existing embedded/textured settings.
   Launch that separate app using its verified `--run` and **previously pinned,
   locally owned** disc/ROM paths. Redirect stdout only to a repo-private log.
   Enter actual normal-shader Sanity Beach gameplay within the 90-second budget;
   move Crash, exercise pause/path transitions, then stop only that test PID.
   This step was **not executed in this turn**. Existing external-cache runners
   are not invoked under this turn's repo-only write permission.
3. Audit with `python -m tools.assess_world_source_probe PRIVATE_STDOUT_LOG`.
   Require at least one source-owned, nondegenerate three-vertex receipt with
   zero errors; review the actual process/disc provenance and scene manually.
   No receipts is a failed native gate, not proof that no source seam exists.

**Render triangles are not an authentic collider.** Static collision uses loaded
neighbor-zone `entry.items[1]` / `zone_rect` / octree nodes, not WGEO packets:
`formats/zdat.h:84`, `level.c:1359` `ZoneQueryOctrees`,
`solid.c:959` recursive node queries and `solid.c:103`
`TransSmoothStopAtSolid`. Solid leaves, bounds, flags and neighbor residency
need their own source/lifecycle proof. Crates/objects additionally use original
GOOL bounds and `gool.c:3694` `GoolCollide`; they are not static mesh solids.
Next source extraction should bound/read the resolved neighbor zone rectangle
and native query leaves (<=512), compare those bounds/solid flags to the pinned
collision oracle at known original points, and prove lifecycle/units before
loading any mapped surface into Mario. No native query is invoked by G1.

G1 runtime acceptance, complete centre-scene depth, real shared collision/input,
G2-G6 and playable fusion remain **BLOCKED/NOT_TESTED**, not inferred from mocks.
The initial implementation did not launch a game. The reviewed private attempt
and current replay are documented at the top. No asset/binary is versioned,
no original checkout or sealed game is edited, and main/other branches are untouched.
