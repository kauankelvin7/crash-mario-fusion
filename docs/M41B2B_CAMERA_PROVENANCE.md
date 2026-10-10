# M4.1B2B0 — Original Crash camera provenance, NOT full shared world view

**Scope:** first native-validated, **read-only source-grounded camera observation**
inside the genuine pinned original Crash Windows game while original libsm64 Mario
still runs in the same process. The complete M4.1B2B world-camera/FBO/occlusion
gate is **NOT complete**. Keep M4.2 authentic Crash physical collision BLOCKED.

## Sources and architecture review

Original source pins: CrashBandicoot-Launcher
`224da7757920a817de2d9242416f657ab95782ea`; original public Crash decompilation
`c1` `256fdcef59f15a190290cc19db3fa9a707843b69`; original libsm64
`fd11813208272b4271d92bd92feb8f3fdbe61be5`.

On 2026-10-10, the authorized Windows **Codex CLI** ran as a strictly
**read-only camera/depth architecture reviewer**, with original pinned
public files. Its source-based findings were:
- Original Crash `c1/src/gfx.c` has guest camera translation `cam_trans`
  at `0x80057864`, camera rotation `cam_rot` at `0x80057870`,
  original unscaled `mn_cam_rot` at `0x800577C4`, **render-prepared
  matrices** `ms_cam_rot`/`ms_cam_rot2` at
  `0x800577E4`/`0x80057804`, and original projection
  `screen_proj` at `0x800578D0`. `GfxUpdateMatrices`
  (`0x80017A14`) applies axis inversions and scaling to render matrices.
  Therefore **`ms_cam_rot` is not a pure world-to-camera orientation**.
- Pinned Crash Launcher `FramePacing.NativeWideRenderer.cs` reads the
  render-prepared 3×3 signed matrix at `0x800577E4`, projection scalar at
  `0x800578D0`, GPU/GTE offsets and draw rectangle. That
  **host-derived** wider-field projection is not bit-exact evidence of all
  original PS1 GTE clipping/saturation.
- `GlDisplayRt` stores a host `DepthComponent24` renderbuffer, but the
  backend uses its depth for **selected native-wide world/side passes**, not
  every original PS1 retail-centre primitive. The central retail rendering
  depends on ordered PS1 OT primitives, *not* a complete original depth
  texture. Backend depth uses a host `1 - clamp(64/Z)` mapping. **No
  claim of a complete Crash depth buffer or shared Mario occlusion is
  justified**.
- Stronger evidence for 3D fusion will require correlating a **same-pass**
  camera snapshot to a known original GTE SXY/Z projected vertex and original
  world source/OT-generation identity, then measuring depth coverage inside
  the original full 4:3 image. If a visible original centre-world opaque
  polygon has only cleared depth 1.0, the existing FBO cannot provide
  complete occlusion.

The read-only Codex review did not edit code, launch the game, or access any
retail ROM/disc. The on-device engineering assistant implemented and tested
the next bounded probe separately.

## New reversible read-only diagnostic

`integration/embedded_mario/CrashCameraProbe.cs` is an opt-in
`CM64_CAMERA_PROBE=1` companion to the already isolated
`cm64-embedded-mario` mod; it **never** changes the Crash camera,
guest pad state, RAM, original native collision or original renderer.

- Subscribes to **PadReadEvent, phase=PAD_UNKNOWN**, not an original
  postphysics camera frame. Reads **only `PSMemory.Ram`** as raw 2 MiB
  little-endian bytes, avoiding `IMemory.ReadU32`'s potential
  guest VBlank/Count side effects.
- Requires the pinned original game's known **LevelKind.Gameplay**, a valid
  projection in `1..4096`, nonzero nine-entry signed `ms_cam_rot`,
  valid in-RAM zone/path references, conservative native pause/Start filter
  and bounded native read spans. Raw signed fixed-point translation, original
  projection, zone/path/progress and matrix are never transformed or
  applied to Mario; every line includes `safe_for_shared_depth=false`.
- Bounded to **48 accepted samples, 90 seconds maximum, <=~1 Hz**;
  opt-out/unload removes only its event callback, with failures contained.
  If a level/path/zone changes or a callback gap occurs, the observer
  increments its **diagnostic epoch**. This epoch is not a guest object
  allocation generation or postphysics stamp.
- Python `tools.assess_camera_probe` audits **private local stdout
  only**. It rejects wrong phase, malformed/missing s16 matrix, invalid
  raw pointers, nonmonotonic sequences, scope mixing, only two samples and
  stationary scenes. Its acceptance criterion is **>=3 camera samples in
  one level/epoch/zone/path** with at least **two actual raw
  matrix/translation/path-progress changes**. Passing means only
  `RAW_ORIGINAL_CAMERA_VARIATION_ONLY`; the result explicitly sets
  `postphysics=false, depth_complete=false, camera_calibrated=false`.
  It cannot be used as a camera transform until next source gate.

## Native Windows evidence, separately from mocks

First in-level attempt was **not verified**: scoped navigation stopped at
Sanity Beach's island-selection map and the probe reported 0 native camera
samples. No inference about absent camera was made.

A second bounded original Crash Windows session entered **Sanity Beach
gameplay, original level ID 9**, with only the original-game process receiving
operator-approved, PID-verified local HWND keystrokes. The private
in-game `PrintWindow` image showed Crash and the textured original Mario mesh
in front of beach crates. The guest source probe printed **24 bounded raw
camera observations over five diagnostic path/epoch scopes**. Source projection
was **288** and the valid guest RAM zone/path addresses remained bounded.
One stable original scene/epoch yielded **3 sequential raw camera samples
with 2 actual changes**, while a later 17-sample stationary scope was
properly rejected as nonmoving by the auditor. The source-only statement:
`CAMERA_SOURCE_GATE verified=True reason=RAW_ORIGINAL_CAMERA_VARIATION_ONLY
samples=24 scope_samples=3 changed=2 level=9 epoch=1
postphysics=False depth_complete=False camera_calibrated=False`, exit 0.

The native original Crash process and Mario simulation remained responsive
and all local original-game sessions ended; **private logs, captures, ROM,
Crash BIN/CUE, atlas and binaries remain only under LOCALAPPDATA**.
This source observer is distinct from the original Mario native CPU/UV/FBO
render milestones, which remain unchanged and do **not** gain calibrated
camera/depth by virtue of this test.

Full asset-free Windows source/native-reference regression on this branch:
**140/140 PASS**, 0 failures, preserving 130 earlier tests and adding 10
camera-source/malformed-scope tests. These Python mocks are **NOT** original
commercial-game execution evidence.

## Reproduce with your own original files

```powershell
cd "$env:USERPROFILE\Desktop\Projetos\crash-mario-camera"
./tools/windows/Build-CameraProbe.ps1 -CheckOnly
./tools/windows/Build-CameraProbe.ps1
./tools/windows/Run-CameraProbe.ps1 -MarioRom "PATH_TO_YOUR_ORIGINAL_SM64_US_ROM" -CrashDisc "PATH_TO_YOUR_ORIGINAL_CRASH_CUE" -CheckOnly
./tools/windows/Run-CameraProbe.ps1 -MarioRom "PATH_TO_YOUR_ORIGINAL_SM64_US_ROM" -CrashDisc "PATH_TO_YOUR_ORIGINAL_CRASH_CUE" -Seconds 90
```

**After starting the finite game test, enter Sanity Beach and move Crash in
the level.** Without real in-level original camera samples, the scripted
camera evidence gate intentionally **fails nonzero**. All local private
session logs are stored in `%LOCALAPPDATA%/CrashMarioFusion/M41B2B-camera`.
Run the isolated asset-free audit on a *known, private* session log with
`python -m tools.assess_camera_probe --private-log "PRIVATE_HOST_LOG"`.
Never upload private source-camera logs, private screenshot or user-owned
game data to GitHub.

## Next M4.1B2B gates — NOT DONE

1. **Same-pass original scene camera contract**: capture after
   `GfxTransformWorlds` at a verified original source seam,
   including original GTE offsets, source zone/OT provenance and immutable
   scene generation IDs; compare >=3 actual original GTE SXY/Z vertices
   to host-projected vertices without relying on authored 2D anchors.
2. **True depth coverage**: separate render-target/depth attachment
   generation ownership; instrument original centre and native-wide side
   polygons, test complete opaque coverage and occlusion before committing
   to a Mario GL/FBO depth strategy.
3. **M4.2 native collision**: authentic Crash source volume/material,
   stable lifecycle, Mario native grounded movement and an actual shared
   solid-object interaction. All remain blocked.

### Independent final scripted native original-game gate

After the first successful 24-sample camera-scene session, a separate
**90-second original Windows Crash process** was started by the committed,
hash-sealed `Run-CameraProbe.ps1` script. An independent bounded operator
used ONLY PID/HWND-verified `PostMessageW` keys to enter actual Sanity
Beach gameplay and move the original Crash character, without sending input
to other desktop windows. The host compiled the original Mario mesh and
texture and remained responsive. The private CameraProbe captured **48
raw guest camera samples** before its 48-record cap, level=9; the same-scope
audit found three consecutive records with two real changes.
```text
CAMERA_SOURCE_GATE verified=True reason=RAW_ORIGINAL_CAMERA_VARIATION_ONLY samples=48 scope_samples=3 changed=2 level=9 epoch=1 postphysics=False depth_complete=False camera_calibrated=False
M41B2B_CAMERA_GATE passed=True camera_source_varied=True mario_mesh=True texture_gpu=True responsive=True depth_complete=false
FULL_ORIGINAL_CAMERA_PROBE_RC=0
```
The self-terminating script stopped only its own original game PID.
The second session verifies **end-to-end reproducibility of the public
camera audit gate**, not calibrated camera matrices, original full-depth
occlusion, or shared collision. The full game logs, uncompressed ROM/PS1
disc and screenshots remain private.
