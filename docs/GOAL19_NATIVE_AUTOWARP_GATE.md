# GOAL #19 — real original level + native Mario authored-floor controls

**2026-10-10. Experimental, NOT a playable shared-world fusion.** Acceptance: https://github.com/kauankelvin7/crash-mario-fusion/issues/19

## Source change

`CM64_GOAL19_NATIVE_AUTOWARP=1` is strictly opt-in and requires `CM64_EMBED_ENABLE=1`, `CM64_LIVE_CONTROLS=1`, and `CM64_INOUTPUT=1`. The mod calls the **existing original pinned RecompOne host** `CheatManager.RequestWarp(9, 1)`, exactly the developer-menu warp to *N. Sanity Beach*. It never uses a hard-coded memory load/guest patch, starts no independent game, and does not infer an original frame/OT/collider from a menu transition.

The existing `PadReadEvent` observer independently reads the original game RAM level ID `0x80056710` and validates original gameplay level category and both unpaused flags `0x80056400`/`0x8005640C`. For level 9 it emits a bounded **single** `ORIGINAL_SCENE_OBSERVED` receipt. This is a source-owned guest input-poll observation, **not** postphysics or synchronous world GTE projection. The opt-in warp and receipt are disabled by default.

`tools/windows/Test-Goal19NativeAutoWarp.ps1` checks the unmodified M43 private sealed host and original ROM hash, uses only the owner's local Crash disc, requires `-ApproveHumanRun`, and runs a separate private app under `LOCALAPPDATA/CrashMarioFusion/M44-native-warp`. Native traces/logs and the derived original executable stay under `LOCALAPPDATA` only. No game ROM, PS1 disc, screenshot, private trace, executable or generated retail code is distributed. It preserves the source pins and `main`.

## Native Windows evidence (real original games, not CI fixtures)

**Run 1:** private `M43-input/autowarp-ec57143bd5bb4d3185f138f1429d27a4`, 100 seconds, original Crash game launched and entered genuine N. Sanity Beach. Host logged `HOST_DEV_WARP_REQUESTED` then `ORIGINAL_SCENE_OBSERVED level=9`, libsm64 native solver `INIT_OK`, original 704x64 Mario atlas uploaded and `M41B2_TEXTURED_MESH_DREW`. The independent native audit passed on **1,811** Mario ticks: native X/Z movement, input-caused jump/ascent/landing, 30 Hz cadence. A local private screenshot captures Crash, original world and tiny textured 3D Mario next to the **green authored test-floor outline**. This is **not** a common collision volume.

**Run 2:** exact new `Test-Goal19NativeAutoWarp.ps1` original Windows run, 90 seconds, private `M43-input/autowarp-6a6a3db3e72e42beaea8e0b1f08857bb`. Automatic level warp and native scene receipt PASS; original mesh draw PASS; stderr 0; process responsive and stopped. Final strict input audit **1,928 ticks PASS** (`native_x_displacement=true`, `native_z_displacement=true`, `input_jump_air_land=true`, `cadence_30hz=true`), and explicitly `authentic_crash_collision=false`, `surface=AUTHORED_NOT_CRASH`, `human_playability=NOT_CERTIFIED`. Focus was acquired only on the exact original game PID/HWND; mouse and keys were dispatched only after foreground ownership verification. No unscoped global keyboard automation or OS security changes.

**Fail-closed negative control after guard reordering:** a separate 45-second original Windows run reached level 9, was responsive and stopped with empty stderr, but no focused original-image Mario input ticks or mesh draw were observed. The bounded gate correctly failed (`Expected 90..3600 actual native ticks`) and retained private diagnostics; this does not pass Mario control. The preceding independent 90-second run remains the successful native control proof. The runner later corrected explicit JSON `false` values instead of null in failure summary fields.

The existing source-only suite had **181 Python tests, 2 skipped** before the final guard reordering, and the runner `-CheckOnly` passed. These tests are `VERIFIED_SYNTHETIC`; the two independent authorized original sessions above are `VERIFIED_REAL` **only for original-game level entry and native Mario authored-floor input/mesh**.

## How to reproduce locally

1. Use only the existing privately owned NTSC-U Mario ROM and original Crash disc already under `LOCALAPPDATA/CrashMarioFusion`.
2. Run `tools/windows/Test-Goal19NativeAutoWarp.ps1 -MarioRom <private ROM path> -CrashDisc <private .cue path> -CheckOnly`.
3. After native private preflight, run the same with `-Seconds 90 -ApproveHumanRun`. Click inside the original focused Crash image, move Mario with I/J/K/L, and use U to jump, then release keys. The original scene is reached automatically; no developer-menu clicking required.
4. The runner writes a private `summary.json` and either reports `GOAL19_NATIVE_AUTHORED_INPUT_PASS` or fails closed with all evidence retained privately.

## What remains BLOCKED before accepting issue #19

- G1: source-owned matching original GTE/OT world/camera/depth *per frame*. Two previous bounded original-world probes returned **zero** accepted receipts, even with in-level gameplay. See `M42_G1_WORLD_SOURCE_GATE.md`.
- G2: original Mario GPU depth renderer is tested in a native Windows hardware fixture, but has **no source-correct Crash clip-frame producer or complete retail-centre depth**. The displayed small Mario is still an **ImGui/screen-space overlay**, not depth-occluded by world polygons.
- G3: the real Crash collision-query diagnostics are strict and source-backed but don't prove allocation lifetime, material semantics and frames. **Mario remains on the authored Y=0 floor**; do not manufacture collision triangles.
- G4: **PARTIAL REAL**: native Mario 30 Hz x/z, jump and landing proved; independent original Crash steering in the exact same session and restarts/pauses still need verified control evidence.
- G5/G6: physical interaction with the *same* original Crash object and reliable, playable same-world end-to-end game are **NOT VERIFIED**.
- G7: no distribution of original commercial media, derived binaries or private captures; preserved.

**Do not merge main, close #19, tag a release, or call the game fully playable.**
