# M4.1B1 — Mario native mesh painted on the original Crash OutputPanel image

Status: **VERIFIED_REAL Windows original-runtime screen-space output overlay**, not
full world-space calibrated renderer/collision. Branch `feat/m41b-output-overlay`
stacked on M4.1A draft PR #15. M4.1B full textured guest FBO, genuine scene
depth, physical camera and colliders remain **BLOCKED**.

## Why this is a separate stage

The pinned public Crash Launcher `224da7757920a817de2d9242416f657ab95782ea`
displays the original game through `HostWindow.OnRender ->
OutputPanel.DrawImage -> ImGui.Image(original Crash texture)`. There was no
public `OutputPanel` callback exposing the exact letterboxed image rectangle.
M4.1A put Mario in an **independent** diagnostics window; M4.1B1 requires that
Mario actually appears **over the native game image itself**.

A pinned, clean public Crash **clone under private LOCALAPPDATA**, never the
original or sealed M3/M4 host, gets two exact source transformations by
`tools.prepare_m41b_host`:
1. `MenuRegistry`: register/unregister guarded output-image overlay callbacks
   under lock, snapshot the registered list when drawing, disable only a
   failed callback. No writes to the guest RAM/controls/renderer.
2. `OutputPanel.DrawImage`: immediately after the original `ImGui.Image`,
   dispatch the callbacks with `GetItemRectMin/Max` (exact image rectangle).
   Both docked and fullscreen paths converge there.

`OriginalMarioOutputOverlay.cs` consumes immutable copies of the original
native libsm64 triangle/vertex color buffers from the existing Mario simulator.
It draws the real Mario triangles into the host ImGui draw list with an explicit
image clip rectangle. It uses a static **AUTHORED screen-space anchor at image
(0.52, 0.67)** and a bounded isometric diagnostic projector; this is *not*
Mario's actual position in a calibrated Crash world. The guest uses native
Mario movement and a **separate authored flat floor**. No shader, input,
camera, render-depth or collision modification to native Crash.

## VERIFIED_REAL native Windows observations

- The private patched `RecompOne.Runtime.dll` compiled under .NET 10
  Windows (MSYS2/GCC remains for the unmodified original libsm64 DLL).
- The private original Crash game executable loaded exactly one mod and
  remained responsive. The mod logged
  `M41B_OUTPUT_OVERLAY_DREW original_triangles=752 original_crash_image_bounds=true
  overlay=true guest_tick_first=7 guest_tick_last=120 camera_calibrated=false
  shared_depth=false shared_collider=false`. This establishes original guest
  triangle drawing with **advancing native ticks**, not a frozen mesh.
- The original Mario solver still recorded **180 native ticks, 180 CPU mesh
  frames, 101 moving frames** with `AUTHORED_NOT_CRASH` collision provenance.
- Private native `PrintWindow` screenshots of only the original Crash
  1280×720 client window were visually inspected: real red-hat Mario triangles
  overlaid **inside the Crash title image**, then over the original **Sanity
  Beach island-selection map** after scoped keyboard inputs. The overlay
  followed the changing original Crash background without the M4.1A separate
  preview window. A subsequent bounded, separately recorded session entered the
  **actual playable Sanity Beach stage** (Enter, Z, Z with PID-scoped key messages).
  Private native 1280x720 PrintWindow screenshot was visually verified: Crash
  stood in front of beach crates and the original colorful Mario mesh was
  overlaid on the same displayed stage image. This is **in-level graphical
  composition evidence only**; the authored Mario screen anchor still has
  no physical stage-coordinate/depth or shared collision authority.
  Screenshots, logs, session paths, user ROM and Crash BIN/CUE stayed private
  on the authorized Windows device and were NOT included in Git/GitHub/CI.
- Private rebuilt host **M41B_OVERLAY_GATE passed=True,
  mario_mesh=True, on_crash_image=True, responsive=True, shared_depth=false**
  with zero exit code. (The final tested branch/compiled host must include
  the actual original guest tick evidence and reviewed thread-safe registry.)

## Rebuild/reproduce with user-owned local game files

```powershell
cd "$env:USERPROFILE\Desktop\Projetos\crash-mario-inworld"
./tools/windows/Build-OutputOverlay.ps1 -CheckOnly
./tools/windows/Build-OutputOverlay.ps1
./tools/windows/Run-OutputOverlay.ps1 -MarioRom "OWNED_ORIGINAL_SM64_US_ROM_PATH" -CrashDisc "OWNED_CRASH_CUE_PATH" -CheckOnly
./tools/windows/Run-OutputOverlay.ps1 -MarioRom "OWNED_ORIGINAL_SM64_US_ROM_PATH" -CrashDisc "OWNED_CRASH_CUE_PATH" -Seconds 45
```

Scripts fail closed on source pin drift, unrecognized private compiler edits,
binary/source hash mismatches, unexpected active mods, wrong local Mario ROM
size/SHA1 or no real guest geometry draw. Only private local runtime source
and test-host binaries are generated outside the repository. The original
sealed game executables and full-sm64ex observer code are not changed.

## Explicit remaining M4.1B2 and gameplay gates

- **M4.1B2**: original Mario UV/textures on the guest mesh, genuine shader/FBO
  with GL state isolation, real Crash camera projection, shared depth/occlusion,
  stable scene/area lifecycle and native frame ownership. An approved ImGui
  screen-space projector alone does not meet this gate.
- **M4.2**: independently verified Crash collision source volumes/materials,
  original guest frame ownership, meaningful real world-coordinate landmarks,
  authorized calibrated transformation, physical surface lifetime.
- **M4.3**: two playable native characters with actual shared object interaction,
  not parallel inputs/sprites. Full SM64 original events/objects remain a
  separate fidelity requirement.

The Codex CLI ran as a **read-only architecture reviewer** on the Windows PC
and supported the precise OutputPanel image-rect hook as a safe *intermediate*
route. It did not edit the code, execute a game or certify full M4.1.

## Final M4.1B1 repeatability gate and regression

Built the reviewed lock-guarded OutputPanel callback implementation via
`tools/windows/Build-OutputOverlay.ps1`; original pinned launcher executable
and original libsm64 native DLL hashes unchanged. A fresh native Windows run
with `Run-OutputOverlay.ps1 -Seconds 36` returned
`M41B_OVERLAY_GATE passed=True mario_mesh=True on_crash_image=True responsive=True shared_depth=false`,
exit **0**. Its actual original-game log confirmed `guest_tick_first=1`,
`guest_tick_last=120`, original **752** guest triangles, **180/180/101**
libsm64 frames and the explicit `drawing=OUTPUT_IMAGE_OVERLAY` marker. The
finite test process was terminated. Independently executed complete local
native Windows source/oracle suite **121/121 PASS**, 0 skips (original 113
plus eight M4.1B1 source-only safety tests). This is evidence for an in-image
display overlay, **not authentic in-stage camera/depth/collision**.
