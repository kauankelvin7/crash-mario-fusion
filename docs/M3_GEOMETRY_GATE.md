# M3 -> M4 collision and geometry gate (source-only groundwork)

**Status (2026-10-09):** preview-only code and tests; no native cross-game collision,
shared renderer, level-geometry extraction or unified world has been implemented.
This document records evidence-backed seams, stopping conditions, and the next
smallest experiment. **Do not request or commit commercial game files.**

## Pinned-source technical observations

| Original-source seam | Verified source evidence | Engineering implication |
| --- | --- | --- |
| Crash player transform | `Matteo842/CrashBandicoot-Launcher` at `224da775...`, `RecompOne.Runtime/Host/FramePacing.cs`, `ObjTransOff=0x80` and X/Y/Z translation | M3 reads the *player transform* only. **It does not prove the Crash level's collision triangles share that data representation or origin.** |
| Mario native surface | `sm64pc/sm64ex` at `d7ca2c0...`, `include/types.h:228`, `struct Surface` stores three `Vec3s` (signed 16-bit XYZ), native normal, type, room and object reference | Mapped float32 vertices are not yet valid native collision vertices. A candidate triangle can collapse when its vertices become signed 16-bit integers. No native material/room ID may be invented. |
| Mario spatial partition | `src/engine/surface_load.c:24-25,111-150,266-292`, static/dynamic 16x16 partitions; `add_surface` adds one surface to potentially multiple cells | A mesh with N triangles may consume **more than N** `SurfaceNode` entries. Check actual available surface and cell-node budgets before any insertion. |
| Pool safety | `src/engine/surface_load.c:43-75`, `alloc_surface_node` increments `gSurfaceNodesAllocated` with a commented ineffective 7000-node guard; `alloc_surface` increments `gSurfacesAllocated` and its `sSurfacePoolSize` comparison does not stop allocation | **No native insertion is safe without explicit bounded allocation / rollback and monitoring of the existing level's occupancy.** Even one surface is NOT categorically safe until occupancy is established. The file describes 2300 surfaces, but actual available capacity is runtime-dependent. |
| Dynamic lifetime | `src/engine/surface_load.c:630-648`, `clear_dynamic_surfaces` resets dynamic partitions and allocation indices when not in time stop | Any future dynamic insert must use the original engine's correct update/lifetime seam, not a one-off pointer retained across level changes. |
| Collision queries | `src/engine/surface_collision.c:512-544`, `find_floor` casts world position to `s16` before querying native partitions, with XZ native bounds | The `floor_query_safe` flag only checks pre-cast numeric bounds. **It does not demonstrate that a floor exists, that a collider was inserted, or that Mario can stand on it.** |

The native geometry collision-loading path also handles triangle normals, surface
classification, room flags, moving-object association, and spatial cells.
Extracting a rendered mesh from Crash or reading a player XYZ value is NOT
equivalent to obtaining collision geometry.

## Implemented offline preparation

- `tools/world_coordinates.py`: maps signed Crash player XYZ to a candidate Mario
  coordinate frame only with explicit operator calibration; checks float32
  round-trip and conservative query range. **No default scale/yaw.**
- `tools/geometry_preflight.py`: consumes a **caller-authored/synthetic**
  triangle index buffer already expressed in Crash *view units* and a
  `FrameMap`. Requires matching level and explicit area label, checks finite
  coordinates, duplicate/degenerate triangles, winding under positive-scale
  Y-axis rotation, float32 quantization, conservative Mario query bounds, and
  **whether s16 vertex truncation would collapse or flip the candidate**.
  A bounded 4096-vertex / 512-triangle preview cap is strictly a defensive
  offline tool limit, **not** a Mario surface-pool budget.
- Its output says `SYNTHETIC_GEOMETRY_PREFLIGHT_ONLY` and explicitly reports
  `engine_collision_inserted=false`,
  `engine_rendering_inserted=false`,
  `native_surface_pool_capacity_verified=false`, and
  `native_material_and_room_verified=false`.
- `tests/test_geometry_preflight.py`: regressions for handedness and winding,
  native signed-short collapse, duplicate/reversed faces, invalid indices,
  bounds, nonfinite values, missing calibration/frame identity and tool caps.
  These tests run without retail files.

Run from the repository root on Python 3.12+:

```bash
python -m unittest discover -s tests -v
```

All new code in this phase is **VERIFIED_SYNTHETIC only**. It uses no original
geometry; a successful synthetic triangle does not satisfy the M4 gate.

## Next native engineering gate (requires local original game runtime)

1. **Obtain real M3 data first:** in the existing paired local Windows session,
   capture signed Crash XYZ while moving horizontally. Validate authentic
   `x_raw`, `y_raw`, `z_raw`, `crash_level`, trace freshness and unchanged
   native controls. Never reuse M2 Y-only logs as if XYZ existed.
2. **Calibrate explicitly:** choose reviewed Crash and Mario level/area anchors
   and at least one separate distance/basis reference; establish scale and
   yaw for that *specific* pair. No calibration inferred from coin position
   alone. Keep raw game data and private trace off Git.
3. **Identify the authoritative collision geometry:** inspect actual Crash
   source runtime collision/NS/GOOL spatial data separately from rendering and
   player transforms. Document provenance, vertex semantics, material behavior,
   solidity and lifetime. Only after this step can an extracted triangle be
   assigned valid source units.
4. **Choose explicit collision ownership:** (A) native Mario engine accepts a
   **bounded and reversible** replica of an original Crash collider, preserving
   Mario's original collision solver; or (B) an evidence-supported reciprocal
   technique. A cosmetic shared camera or draw-only mesh is not a collider.
   State what happens in the other direction, including moving surfaces.
5. **Capacity and lifecycle proof before insertion:** instrument native free
   surface/node counts, spatial partition fan-out, level reload, pause/death
   and object cleanup. Fail closed on inadequate capacity; never rely on
   `alloc_surface` / `alloc_surface_node` ineffective checks.
6. **Minimal real-world test:** inject at most one *reviewed and authorized*
   experimental collision triangle into a **private local build** using a
   validated native seam; instrument original `find_floor` contact/response,
   verify native character grounding and restore state across reload. Include
   a no-insertion control. Never claim shared collisions from an offline
   coordinate transform or a synthetic fixture.
7. **Only then consider visuals:** evidence-backed transform of native render
   geometry in a selected world, camera ownership, synchronization and
   occlusion; no new graphics engine or discarded original simulation.

Do not implement item 6 simply because steps 1-5 were written down.
Stop and record `BLOCKED` if a real source seam/asset provenance/capacity
cannot be verified without local native execution. Continue inexpensive
source-only tests and decisions in the meantime.

## Completion criteria

- Source-only Python/C protocol regression green and separately labeled.
- A real native XYZ session and cross-frame anchors in private local logs.
- Original movement, coin and pause/load behavior preserved.
- One native *measured* collision response with a control condition,
  verified original-engine ground/air state, and safe lifecycle cleanup.
- No commercial files in Git, PR attachments or hosted CI.
- `docs/EVIDENCE.md`, `docs/STATUS.md` and D005/D006 updated to reflect only
  results actually observed. PR remains draft until the real collision gate.
