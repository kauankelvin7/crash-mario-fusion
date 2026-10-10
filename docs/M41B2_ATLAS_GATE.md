# M4.1B2A — Original Mario atlas and UVs inside Crash OutputPanel

**Milestone: VERIFIED_REAL textured image-overlay diagnostic on Windows, not full
M4.1B2 shared-camera or depth-composited renderer.**

Branch `feat/m41b2-mario-texture`, stacked on M4.1B1. Original pins:
CrashBandicoot-Launcher `224da7757920a817de2d9242416f657ab95782ea`,
libsm64 `fd11813208272b4271d92bd92feb8f3fdbe61be5`.
Full-sm64ex original process/observers, M2/M3 milestones, original Crash pad,
guest memory, original launcher binaries and `main` unchanged.

## Implemented

- Original libsm64 `sm64_global_init` generates the native **704 × 64 × 4
  RGBA atlas** directly from the locally owned SM64 US ROM in private memory.
  Only when `CM64_EMBED_ENABLE=1, CM64_INOUTPUT=1, CM64_TEXTURE_ATLAS=1`
  does the opt-in Crash mod copy that atlas to a private managed byte buffer.
  Its own temporary copy is zeroed. No texture/image/ROM is written to Git,
  a screenshot file, an endpoint, CI or the working repository.
- Original `SM64MarioGeometryBuffers.uv` now accompanies position/color
  through immutable, finite-checked, bounded guest frame snapshots, preserving
  each vertex's native UV (six components/triangle).
- A pinned source-only generator, `tools.prepare_m41b2_atlas`, adds a
  host-owned `OriginalMarioAtlas` class to a **private clone** of the pinned
  public Crash runtime. No modifications to original installed launcher/source.
  It queues CPU atlas bytes from the guest and uploads them on Crash's own
  original **GL render thread**, not on VSync. Upload saves/restores active
  GL texture binding, pixel unpack alignment and pixel-unpack PBO binding.
  GPU object deletion is deferred to render/host closing; errors disable the
  texture upload without propagating an exception into original Crash rendering.
- The original Mario output overlay now sorts native triangles and draws
  textured triangles with `ImDrawList.PrimReserve/PrimVtx` using exact
  libsm64 UVs and per-vertex colors, with source image bounds clipping.
  **libsm64 sentinel UV (1,1)** signifies untextured native triangles, which
  remain colored instead of sampling the transparent atlas padding.
  The debug projector is still an **AUTHORED screen-space image overlay**.
- Reproducible bounded private Windows build and original-game smoke scripts
  `Build-TexturedMario.ps1` and `Run-TexturedMario.ps1` verify original
  source/EXE/library hashes, private ROM SHA1/size, exact single enabled mod,
  opted-in atlas, original guest movement frames, actual host texture upload
  and textured guest triangles, with a nonzero result if any gate is absent.
  Each run stops only its own original game process.

## VERIFIED_REAL original Crash evidence (native Windows)

In the authorized original Crash game window, before the final enhanced
exception-handling change, the private host logged:

```text
[cm64-atlas] HOST_GL_ATLAS_UPLOADED width=704 height=64 private=true
[cm64-atlas] M41B2_TEXTURED_MESH_DREW original_textured_triangles=50 native_guest_tick=120 authored_screen_anchor=true shared_camera=false shared_depth=false shared_collider=false
[cm64-output] M41B_OUTPUT_OVERLAY_DREW original_triangles=752 original_crash_image_bounds=true overlay=true guest_tick_first=1 guest_tick_last=120 camera_calibrated=false shared_depth=false shared_collider=false
[cm64-embedded] HOST_SOLVER frames=180 mesh_frames=180 moving_frames=101 ... physical_status=BLOCKED
```

Private original Windows 1280×720 `PrintWindow` client screenshot inspected:
recognizable Mario, now with **eyes, mustache, and facial texture details**,
overlaying Crash's authentic **Sanity Beach island-selection map**.
The screenshot is private under `LOCALAPPDATA` and must not be uploaded or
committed. M4.1B1 separately demonstrated image overlay on the *actual playable
Sanity Beach stage*; M4.1B2A private screenshot itself was captured on
the **island-selection screen**, not a physically shared stage.
The host remained responsive; its native test gate returned
`M41B2_TEXTURE_GATE passed=True mario_mesh=True texture_gpu=True
textured_triangles=True responsive=True shared_depth=false`, exit zero.

Final follow-up after PBO binding restoration and fail-closed upload handling:
rebuilt private host verified against the pinned source generator, and
Run-TexturedMario.ps1 original Windows game returned passed=True,
texture_gpu=True, textured_triangles=True, responsive=True, exit zero.
The complete local Windows Python/native source oracle suite passed 130/130
checks, including nine new M4.1B2A contract tests.

## Reproduction with only your locally owned original files

```powershell
cd "$env:USERPROFILE\Desktop\Projetos\crash-mario-texture"
./tools/windows/Build-TexturedMario.ps1 -CheckOnly
./tools/windows/Build-TexturedMario.ps1
./tools/windows/Run-TexturedMario.ps1 -MarioRom "LOCAL_OWNED_SM64_US.z64" -CrashDisc "LOCAL_OWNED_CRASH.cue" -CheckOnly
./tools/windows/Run-TexturedMario.ps1 -MarioRom "LOCAL_OWNED_SM64_US.z64" -CrashDisc "LOCAL_OWNED_CRASH.cue" -Seconds 40
```

Never put actual private original ROM/disc paths or game assets in commits,
PR descriptions, CI scripts, releases or public screenshots.

## Outstanding gates — NOT completed by M4.1B2A

**M4.1B2B:** prove genuine Crash native camera matrices/frame ownership and
scene transforms; implement true host-owned textured GL/FBO guest composition,
full GL-state/depth and occlusion bridge, including resizing, reload, pause,
scene/area changes, and private original playable-stage capture. The present
view is still an independent isometric camera with a hardcoded image fraction,
not a calibrated 3D shared world; color blending still involves a native
vertex-tint approximation on untextured triangles.

**M4.2:** source-verified Crash physical collider volumes/materials, authoritative
physics frame ordering and 3D coordinate landmarks, atomic guest native
surface creation/removal and native Mario landing/collision on authentic Crash
geometry, not its visual triangles.

**M4.3/M4.4:** real independent gameplay/control for both native characters
with a shared solid object and complete semantic fidelity; libsm64 by itself
does not implement all original SM64 object/events.

Do not merge to `main` or claim finished playable fusion from a textured
screen-space overlay.
