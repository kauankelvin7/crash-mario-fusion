# M4.1A — Original libsm64 CPU mesh visible in original Crash Windows host

## Verified real original-game visual output (2026-10-09)

A separate private copy of the pinned Crash Launcher (not altered upstream source)
successfully loaded exactly one opt-in Mario integration C# source mod and
native libsm64 Windows x64 DLL. This milestone uses the same original Mario
CPU solver and original Mario mesh produced in M4.0, not artist-authored Mario
triangles. The authored floor remains experimental.

The adapter **publishes complete immutable copies of libsm64's actual per-frame
position/color buffers**, from the bounded VSync-driven guest simulation, and
uses the Crash host's existing `MenuRegistry.RegisterWindow` ImGui render
callback to rasterize those triangles. Its orthographic/isometric diagnostic
projector auto-fits Mario to a separate window, sorts guest triangles by guest
depth and clips draw calls. Drawing happens in the original Crash app OpenGL
render path; it never accesses GL from the guest solver callback or changes
Crash's game framebuffer, original GPU backend, native pad bus, RAM or geometry.
No screenshot/image is embedded in source, build outputs or documentation.

**Native Windows console evidence**:
- `[Mods] loaded 1/1 mod(s)`;
- `[cm64-embedded] INIT_OK in Crash process`;
- `[cm64-embedded] M41_PREVIEW_DREW native_mesh=true original_triangles=752 guest_window=true shared_scene=false shared_depth=false`;
- `HOST_SOLVER frames=180 mesh_frames=180 moving_frames=101 surface=AUTHORED_NOT_CRASH drawing=DIAGNOSTIC_PREVIEW_ONLY physical_status=BLOCKED`.

**Independent window-image inspection:** native `PrintWindow` (client-only)
captured the running CrashBandicoot.exe window at 1280×720 to a private file in
`%LOCALAPPDATA%/CrashMarioFusion/M4-embed/m41-print-window.png`.
The image was visually inspected: the actual recognisable multicolor Mario
geometry is visible in the distinct `Mario native geometry | M4.1 diagnostic`
window over the Crash original title scene, with the Developer Menu behind it.
The image remains PRIVATE on the authorized device: not committed, uploaded,
attached to a PR or distributed. A first foreground-based screenshot attempt
failed safely because the browser owned focus; PrintWindow then successfully
captured only the game window without stealing focus.

## Boundaries / what remains

**This is a M4.1A visible-geometry diagnostic, NOT completion of full M4.1
shared-scene renderer.** Mario isn't projected into Crash's stage coordinates,
camera or depth; the image uses ImGui triangles rather than textured guest GL
shaders (colors are from the original libsm64 output), self-centers its
guest view, and does not display moving synchronized Crash colliders. Mario
native physics still uses only the two AUTHORED original-Mario test surfaces.
`MenuRegistry` lacks a built-in callback unregister API; the mod disables
its preview when unloading, but an actual unload/reload lifetime refactor will
be needed before a persistent launcher integration.

**Next M4.1B**: implement host-owned guest framebuffer/texture and camera
projection through an isolated reviewed OpenGL renderer, composite into the
real Crash OutputPanel with restored OpenGL state/depth and correct lifetime.
Verify actual in-stage windows and game state. **M4.2** still needs separately
extracted, independently validated Crash volumetric collision/material
identities and coordinate calibration. Do not infer a shared world from this
preview.

## Repro (user-owned original ROM and disc remain private)

```powershell
cd "$env:USERPROFILE\Desktop\Projetos\crash-mario-render"
./tools/windows/Build-EmbeddedMario.ps1 -CheckOnly
./tools/windows/Build-EmbeddedMario.ps1
./tools/windows/Run-EmbeddedMario.ps1 -MarioRom "PATH_TO_OWNED_US_SM64_ROM" -CrashDisc "PATH_TO_OWNED_CRASH_CUE" -CheckOnly
./tools/windows/Run-EmbeddedMario.ps1 -MarioRom "PATH_TO_OWNED_US_SM64_ROM" -CrashDisc "PATH_TO_OWNED_CRASH_CUE" -Seconds 40 -RequirePreview
```

Only a private test launcher is modified; script verifies the sealed pinned
original Crash binary, original libsm64 pin, enabled mod allowlist, hashes of
source and DLL, private original ROM hash. `RequirePreview` causes a nonzero
test result if real host drawing is absent. CI source-only tests are not claimed
to execute either original game.

## Regression and explicit real preview gate

On authorized Windows, the **113/113** complete Python/native-oracle suite passed (original 108 plus five M4.1 source-only checks). The separate private original-game test with `Run-EmbeddedMario.ps1 -RequirePreview -Seconds 32` passed as `HOSTED_MARIO_RESULT passed=True init=True solver=True preview=True responsive=True physical=BLOCKED`, exit 0. The original Crash process was closed after the finite run, and no commercial assets, images or private logs were added to version control.
