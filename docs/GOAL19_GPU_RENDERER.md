# GOAL #19 — bounded native GPU renderer seam

**EXPERIMENTAL / NOT PLAYABLE.** No original game was launched for this work.
No user ROM/disc, original mesh capture, commercial executable, screenshot or
private native log is included in Git, CI or the PR.

## What exists

The exact pinned public Crash host remains
`224da7757920a817de2d9242416f657ab95782ea`. A disposable source clone under
this worktree's ignored `.cache/goal19-renderer/source` extends the existing
OutputPanel/atlas hook, not the original upstream checkout or another worktree.
Its public runtime compiles natively on Windows with the new source seam.

`OriginalMarioClipFrame` copies one bounded tick's homogeneous clip coordinates,
original UVs and normalized RGB into one owned, interleaved triangle buffer.
All-(1,1) native UV triangles retain the existing untextured sentinel semantics.
The producer must supply attributes from one immutable native frame and a
source-validated projection of that same frame; the constructor cannot certify
where externally supplied clip coordinates came from.

`OriginalMarioGpu.TryRender` is default-off (`CM64_GPU_SELF_DEPTH=1` is required).
It accepts only already-projected clip data: **no camera, axis mapping, Z formula,
authored perspective transform or Crash scene depth is invented here**. GLSL
uses homogeneous `gl_Position` and perspective-correct smooth UV/RGB varyings.
An owned RGBA8 FBO + DepthComponent24 attachment tests/writes each fragment with
LESS. There is no CPU triangle sorting, sprite, static Mario image or scene-depth
sampling. Texture modulation/nearest sampling follows the existing atlas overlay
contract; this is not certification of every original N64 material/render mode.

The original OutputPanel GL dispatcher captures the actual GL object and owner
thread. Other threads/contexts are rejected before any GL access. Every mutated
binding, viewport, mask, depth range/function, polygon mode, clip-distance and
enable state is restored on scope exit, including an incomplete-FBO failure.
Target texture identity survives resize. Each draw resolves the current host
atlas, so a release returns fallback and a reload cannot reuse cached atlas IDs.
Renderer resources are deleted by the GL owner before atlas/backend shutdown.
Wrong-owner shutdown is reported/deferred, never executed on an arbitrary thread
or allowed to interrupt the original host shutdown dispatcher.

## Exact remaining blocker

**No original-game clip-frame producer is connected.**
`OriginalMarioOutputOverlay.cs` stays unchanged as the reversible fallback;
setting the GPU switch alone does not replace its painter-sorted output. This
is an implemented/tested GPU source contract, **not yet an improved original-game
Mario presentation**. Converting raw `ms_cam_rot` to a guessed Matrix4x4, copying
the authored screen anchor into a new camera, or treating host side-pass depth
as complete retail-centre depth would violate the existing camera provenance gate.

The next camera workstream must provide same-render-pass GTE SXY/Z reprojection,
scene/OT generation and source frame identity before submitting original Mario
clip frames. A successful call returns a texture for that frame only; future
composition must use the documented GL bottom-left versus ImGui UV orientation
and must not reuse the result across atlas/session release. It must not clear,
attach, modify or claim ownership of the original Crash framebuffer/depth.

## Reproduce without games or private assets

Windows prerequisites: existing pinned public M0 sources, .NET 10 SDK/public
NuGet dependency cache, MSYS2 GCC/Python. The scripts do not download retail data,
copy a commercial app, load libsm64, tick either game, or change global input.

```powershell
./tools/windows/Build-GpuRenderer.ps1 -CheckOnly
./tools/windows/Test-GpuRenderer.ps1
./tools/windows/Test-GpuRenderer.ps1 -Gpu
```

`-Gpu` opens an invisible synthetic OpenGL fixture, not a game window. All build
outputs, generated source, synthetic sender and logs stay in ignored `.cache`;
process environment is restored. Existing Python and .NET assertions are intact.

## Verification on Windows, 2026-10-10

- Full Python regression: **170 tests PASS**, including the actual pinned public
  host-source seam oracle. No original runtime or owned assets are used.
- Patched public RecompOne runtime: native .NET build PASS. Six existing upstream
  warnings remain; no warning suppression or unrelated source changes.
- Existing .NET contracts: original native CMJ1 sender/event bus **27 checks**,
  Crash pose observer **58 checks**, collision decoder **27 checks**, input
  **17 checks**; exact current counts are recorded by the private runner logs.
- Synthetic native GPU: **37 assertions PASS**, Intel UHD Graphics, OpenGL
  `3.3.0 - Build 32.0.101.5763`; crossing triangles pick different near faces at
  different pixels in either draw order. Nonuniform-w color and 704x64 UV-gradient
  readbacks match numerical perspective interpolation. Release/reload/resize,
  hostile GL state, incomplete FBO, wrong-thread draw/cleanup and full resource
  deletion/recreation are covered. FBO failure is deliberately injected and its
  diagnostic on stderr is expected, not an unhandled error.
- Configured independent `qa_reviewer` was unavailable; no agent review or fresh
  original-game verification is claimed. This proof is **VERIFIED_SYNTHETIC**,
  even though the fixture executes on a real Windows GPU.

Remaining acceptance: original GTE-aligned camera/frame mapping, complete Crash
centre-scene depth, authentic native collision, independently proven controls,
interaction with a common original object, and original Windows gameplay proof.
**Do not merge main, close #19, or call this fully playable.**
