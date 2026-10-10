# M4.2 collision source probe — 2026-10-10

Branch: `feat/m42-authentic-crash-surfaces`, starting commit
`603baf2a47128ee2bafa9a34aeb8c3d8606029ad`.
**G1 remains BLOCKED. G2 is prohibited. No playable-world claim.**

## Source evidence, VERIFIED_SOURCE

All four public caches passed exact HEAD and clean-tree checks; no source pins
were changed:
- c1: `256fdcef59f15a190290cc19db3fa9a707843b69`.
- Crash Launcher: `224da7757920a817de2d9242416f657ab95782ea`.
- libsm64: `fd11813208272b4271d92bd92feb8f3fdbe61be5`.
- sm64ex: `d7ca2c04364a6dd0dac58b47151e04e26887e6f0`.

Pinned c1, relative to its public root:
- `src/ns.h:12`: entry magic `0x100FFFF`, 32-bit guest entry header and
  at most 128 items. `src/ns.c:195` computes an item's extent from the next
  item pointer. `NSPageTranslateOffsets`, `src/ns.c:270`, translates the
  extra terminal pointer too. These are resident pointers, not disk offsets.
- `src/formats/zdat.h:84`: collision item has signed xyz, unsigned whd,
  an unknown word, then root and three uint16 maximum depths at offset 28.
  Rendered `zone_world` polygons are a separate structure, not this octree.
- `src/solid.c:959`, `ZoneQueryOctreeR`: zero is empty, odd is a leaf,
  even is a byte offset from the zone rectangle to child uint16 values.
  Child order is x/y/z nested loops; each axis splits only below its own
  maximum depth. `ZoneQueryOctree`, `src/solid.c:1017`, shifts source
  origins and dimensions by 8. That establishes Crash raw fixed-point
  bounds only, **not a Crash-to-Mario scale or coordinate transform**.
- `src/solid.c:210`, `ProcessNode`, can generate drowning, burning,
  explosion, death and other native events. Raw nodes are retained verbatim;
  the probe does not rename all odd leaves to ordinary solids/materials.
- `src/solid.c:1164`, `FindFloorY`, separately accumulates support heights
  and averages eligible nodes; `PlotQueryWalls` also has type/subtype-specific
  filtering. Six box triangles or two top triangles are not automatically
  equivalent to these algorithms.
- `src/level.c:21` declares `cur_zone` at `0x80057914` and `cur_path` at
  `0x8005791C`. `ZoneQueryOctrees`, `src/level.c:1359`, guest function
  `0x800294B0`, queries **resident neighbors** resolved with `NSLookup`,
  using original query bounds, not only the camera's current zone.
- `src/gool.c:1667` and surrounding object-bound update code derives object
  bounds using native translation, rotations and animation-dependent state.
  Static zone leaves do not represent moving GOOL crates/objects.

Pinned Launcher:
- `RecompOne.Runtime/Memory/PSMemory.cs:24` exposes a read-only RAM Span.
  Ordinary memory reads can trigger `CountAccess` and VBlank catch-up;
  therefore the probe never calls `IMemory.ReadU32` or writes guest memory.
- `RecompOne.Runtime/Events/RuntimeEvents/PadReadEvent.cs:4` is an active-low
  controller-read callback, **not** a postphysics boundary or allocation stamp.
- `RecompOne.Runtime/Host/FramePacing.Hooks.cs:18` and
  `Host/FramePacing.cs:257` distinguish original object/world call hooks.
  This probe does not replace those hooks or the renderer.

Pinned original libsm64:
- `src/libsm64.h`, `SM64Surface`/`SM64SurfaceObject`: signed integer
  triangle vertices, separate native type/force/terrain, and explicit
  object transforms. `src/libsm64.c:621` exposes object create/move/delete.
- `src/load_surfaces.c:94`, `engine_surface_from_lib_surface`, computes
  normals from triangles and applies guest object transforms.
  Static loading and dynamic object ownership are native library globals;
  no lifecycle-safe insertion or material mapping follows from an octree
  pointer alone. Existing `integration/embedded_mario/Interop.cs` supplies
  the original ABI, but its authored floor is an experiment, not G2 evidence.

The current upstream Universal Modder mashup skill was consulted. Its embedded
original-library route and ownership/oracle guidance do not authorize treating
render geometry or invented collision constants as original collision.

## Implemented, reversible diagnostic

`integration/crash_collision/CrashOctree.cs` parses only bounded raw RAM and
the resident source collision item. It validates entry magic/table/span,
signed endpoints, depth, child extents, cycles, exact subdivisions, 8192 visits
and 4096 leaves. Any violation rejects the entire observation, never truncates
and never constructs triangles. Unknown raw leaf encodings stay raw.

`CrashCollisionMod.cs` opts in via `CM64_COLLISION_PROBE=1` and subscribes only
to port-zero PadRead. It requires original Sanity Beach level 9, valid native
actor/path pointers, and unpaused/non-Start input. It captures at most 24
records in 90 seconds, at most one accepted record per second, and unregisters
on unload/timeout. Every record includes version/pins, level, scene identity,
actor zone, raw position, exact source item span, source digest and all decoded
volume bounds. Records stay in private AppData stdout only, never in fixtures.

The **observer epoch** invalidates on memory/identity/digest changes,
pause/non-gameplay/invalid callbacks and callback gaps. It explicitly does
not establish a guest allocation generation, original query ownership,
neighbor coverage or postphysics frame coherence. Every emitted record states
those limitations; no Mario solver or authored floor is started in this mode.

`tools/assess_crash_collision.py` validates private protocol records without
printing geometry. It checks pins, numerical domains, spans, volume subdivision,
stable scene digest, sequence/epoch and movement. It rejects attempted promotion
to unknown postphysics/provenance claims. Even valid diagnostic traces leave
**g1_passed=false, g2_allowed=false, exit 2**. Passing a schema is not G1.
Unrelated OEM host output is ignored as bytes; protocol JSON must remain UTF-8.

Build/run scripts verify sealed original hashes, copy only host software into
`$env:LOCALAPPDATA/CrashMarioFusion/M42-playable/collision-probe`, enable exactly
one diagnostic mod and preserve prior builds. They do not copy the sealed
`game`, `save` or `logs` directories, or the owned PS1 disc. Native test writes
and any new game cache remain in M42. Runs stop only their own process after
25–90 seconds, keep private stdout/stderr/audit and return BLOCKED rather than
silently moving to G2. No original renderer, commercial disc or prior runtime
was modified. The separate visual-fidelity worktree was not touched.

## Executed proof

### VERIFIED_SYNTHETIC, source-only native Windows

Existing .NET SDK **10.0.401** built the actual decoder test executable:
```powershell
$cache = "$env:LOCALAPPDATA/CrashMarioFusion"
& "$cache/M0/dotnet/dotnet.exe" build tests/CrashOctree.Tests.csproj -v quiet --artifacts-path "$cache/M42-playable/tests" -p:RestoreIgnoreFailedSources=true
& "$cache/M0/dotnet/dotnet.exe" "$cache/M42-playable/tests/bin/CrashOctree.Tests/debug/CrashOctree.Tests.dll"
```
Result: build exit 0, no warnings/errors; initially 25 checks, then **27 checks**
after adding exact traversal/leaf-cap rejection fixtures, executable exit 0.
Fixtures cover negative coordinates, anisotropic x/z subdivision and child
order, immutable RAM, bad spans/magic/count/depth, overflow, empty trees and
cycles. They are authored bytes, not original-game evidence.

Windows Python **3.14.5** / MinGW GCC **16.1.0** source-oracle command:
```powershell
$env:PATH = "C:/msys64/mingw64/bin;C:/msys64/usr/bin;" + $env:PATH
$env:CM64_C1_ROOT = "$cache/M0/c1"
$env:CM64_SM64EX_ROOT = "$cache/M0/sm64ex"
$env:TMP = $env:TEMP = $env:TMPDIR = "$cache/M42-playable/source-tests"
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'core.autocrlf'
$env:GIT_CONFIG_VALUE_0 = 'input'
& C:/msys64/mingw64/bin/python.exe -m unittest tests.test_volume_boundary tests.test_crash_collision -v
```
Result: **14 tests passed**, exit 0: 9 new audit tests and 5 existing volume
tests. The existing oracle compiles unchanged pinned c1 query slices and
unchanged **sm64ex** collision code, not libsm64 or a retail runtime.
Its overlapping-support counterexample remains **Crash 40 versus Mario 48**
in authored reference units. This falsifies automatic top-triangle equivalence.
The first oracle attempt failed a clean-source check under mixed Windows/MSYS
line-ending configuration; rerunning with the existing documented input
normalization passed without changing upstream files.

Final broader source-only regression, with the same environment:
```powershell
& C:/msys64/mingw64/bin/python.exe -m unittest discover -s tests -v
```
Result: **149 tests passed**, exit 0. No commercial runtime was launched by this
suite. The .NET test was rebuilt separately and passed 27 checks again.

### VERIFIED_REAL, narrow raw extraction only; G1 BLOCKED

Executed on the authorized native Windows desktop:
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/windows/Build-CollisionProbe.ps1 -CheckOnly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/windows/Build-CollisionProbe.ps1
$settings = Get-Content "$cache/M3-crash-pose/app/settings.json" -Raw | ConvertFrom-Json
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/windows/Run-CollisionProbe.ps1 -CrashDisc $settings.CdPath -CheckOnly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/windows/Run-CollisionProbe.ps1 -CrashDisc $settings.CdPath -Seconds 90
```
Both preflights and private build returned 0. A fresh original Crash process
loaded **1/1 diagnostic mod**, remained responsive and produced no stderr.
PID/HWND-verified Enter and Cross/Z messages used the existing native operator
harness only against the new M42 app. No global keyboard or screenshot capture
was used. It emitted **one actual level-9 source-volume record**; that record
passed the independent schema/bounds validation. Other eligible observations
were rejected with **TRAVERSAL_LIMIT**. The cap was not relaxed to make a run
pass. A later movement request found no window after timeout and failed closed;
no movement or shared contact is claimed.

The initial strict audit was BLOCKED by unrelated OEM host-log encoding.
After the byte-oriented parsing fix and regression test, re-auditing the same
private recording returned **exit 2, SAMPLE_COUNT, samples=1**. That re-audit
is validation of saved evidence, **not another native run**. Full-stage
extraction, stable moving-scene diagnostics, physics contacts and G1 have
**not passed**. Private geometry/telemetry/binaries were not added to Git.

## Concrete next native step, without weakening G1

1. Use the pinned original `ZoneQueryOctrees` call at `0x800294B0` as the
   source query boundary. Validate the actual native query pointer, descriptor
   count, sentinel and `nodes_bound` from `src/level.h:61`; preserve original
   queried neighbor EIDs/item identities. The complete camera-zone tree can
   exceed diagnostic budgets. Do not simply raise caps or substitute an
   actor-centered authored cube. First instrument/count the original bounded
   query and prove its RAM layout against the native binary and c1 oracle.
2. Correlate input/query/result/object physics phases in one original frame,
   including skipped/repeated host updates. Add an original reload/allocation
   boundary; digest+address alone cannot detect same-address reuse. Abort on
   pause, warp/restart, neighbor replacement or changed lifetime.
3. Compare real eligible nodes/events/floor and wall queries before selecting
   any subset/material conversion. The original averaging counterexample
   requires an explicit limited-slice proof or a different native contact seam;
   turning each leaf into six faces is not a justified fix.
4. Only after G1 and matched **real source landmarks** establish coordinate
   axes/scale/error bounds should G2 create bounded libsm64 surfaces, with
   original object deletion/reload ownership and **no authored fallback**.
   G3 full 3D/camera/depth, G4 independent controls and G5 original shared-object
   contact remain blocked; the existing overlay cannot satisfy them.

The current strict private script is runnable again with the same verified
owned disc. It intentionally exits 2 until the missing source/query evidence
is implemented and verified; it is a diagnostic gate, not a playable launcher.
