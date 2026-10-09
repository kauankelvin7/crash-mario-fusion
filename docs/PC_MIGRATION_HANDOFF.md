# PC migration / exact continuation checkpoint — 2026-10-09

## Canonical remote checkpoint

Repository: https://github.com/kauankelvin7/crash-mario-fusion
Remote **feature** branch: `feat/m3-coordinate-contract`
Latest proven published source commit before this handoff: `da6e15f03fae5d8767a7a73af77757a6a0a7f139`.
Draft PR: https://github.com/kauankelvin7/crash-mario-fusion/pull/2 (base `m0-recon`; **not merged**).
This handoff is documentation only, built on top of the checkpoint. Original `main`/`m0-recon` intentionally unchanged.

**Status: M3.2 diagnostic Crash observer implemented and source/native fixture tested, real runtime diagnostic packet gate NOT PASSED.** Crash/Mario are still separate windows, worlds, collision solvers and cameras; no playable fusion, geometry sharing, cross-engine frame calibration or native post-physics Crash observation.

### Verified results on previous Windows PC

- M2 real native Mario coin => guarded Crash input/jump/ground trace, with prior user-observed behavior (see `docs/EVIDENCE.md`).
- M3.1 REAL native Mario CMW1 read-only pose collector: 1,137 accepted samples, 0 rejected, native level 16 / area 1 and varying XYZ; no proven Mario level/area transition or independently marked pause event.
- M3.2 source: `integration/crash_pose/CrashPoseMod.cs` is opt-in, <=10 Hz, <=300 s/3,000 attempts, sends UDP localhost only, observes signed native XYZ/rotation/level with a read-only RAM span, guards pause/lifecycle, and **never changes player memory or inputs**. It samples `PadReadEvent`; CMW1 phase `0` `UNKNOWN_DIAGNOSTIC`, NOT known native postphysics.
- 7/7 new Crash Python tests, 49/49 full Python, 58/58 native Crash adapter fixtures via original RecompOne mod compiler and event bus, 27/27 original integration fixtures and 17/17 native geometry fixtures passed on the old Windows PC.
- Isolated private native Crash launcher built under `%LOCALAPPDATA%\CrashMarioFusion\M3-crash-pose\app` with zero warnings/errors; manifest verified. This directory and binary are **not in GitHub**.
- Remote source CI previously passed for commit `da6e15f`. These checks do **not** mean that the M3.2 Crash live packet collection worked.

### Last run / precise blocker (2026-10-09)

An operator tried the new Crash collector. The private launcher did load its new mod and passed disc identification, but showed:

```text
[cm64-crash-pose] ready phase=UNKNOWN tick=observer_pad_callback NOT_CALIBRATION_READY
[Host] window unavailable: GlfwException: ApiUnavailable: WGL: The driver does not appear to support OpenGL
```

The old PC had insufficient native OpenGL 4.3 support. Earlier validated M0 Crash runtime successfully used **app-local** Mesa3D 26.2.4 x64 (`opengl32.dll` and `libgallium_wgl.dll`), not a system driver change. Those two DLLs were copied into the private **M3** app folder on the old PC after the failed run; no Mesa binaries were checked into Git.

At the end of investigation a prior CrashBandicoot process **PID 12200** in Windows session 19 remained running with **MainWindowHandle=0**; process termination attempts returned access denied / EPERM. A second private collector attempt produced 0 packets and no meaningful new game log, while the old windowless process persisted. **Root cause of the second run is NOT established; do not assert it was definitely the orphan.** The old machine may need manual Task Manager intervention, sign-out or restart if reused. That specific PID has no relevance on the new computer. No further code edits were made after source commit `da6e15f`; this documentation records the stopped checkpoint.

## Resume on a completely new Windows 10/11 x64 PC

Install **Git**, **PowerShell 7**, and official **MSYS2** (https://www.msys2.org/), fully update MSYS2 as documented. Python is installed through the project's MSYS2 setup; additional external dependencies are fetched by source-pinned scripts (require network, permissions and disk space).

From PowerShell 7:

```powershell
git clone --branch feat/m3-coordinate-contract https://github.com/kauankelvin7/crash-mario-fusion.git
cd crash-mario-fusion
git status --short --branch
git log -1 --oneline
# Set process-local tool PATH (not a system configuration):
$env:PATH = 'C:\msys64\mingw64\bin;' + $env:PATH

./tools/windows/Setup.ps1
# Verify source-only tests before building games:
& 'C:\msys64\mingw64\bin\python.exe' -m unittest discover -s tests -v
./tools/windows/Test-CrashPose.ps1
./tools/windows/Test-Integration.ps1
./tools/windows/Test-Geometry.ps1
# Compile fresh, isolated Crash diagnostic app WITHOUT launching it:
./tools/windows/Build-CrashPose.ps1
```

`Setup.ps1` clones/pins public CrashBandicoot-Launcher `224da7757920a817de2d9242416f657ab95782ea`, sm64ex `d7ca2c04364a6dd0dac58b47151e04e26887e6f0`, libsm64 `fd11813208272b4271d92bd92feb8f3fdbe61be5`, installs .NET SDK **10.0.401** in private cache and tool packages. The new PC is expected to need this; **the old PC's private compiled binaries and ROMs are not in Git**. `Build-CrashPose.ps1` is for a *fresh isolated private directory*; it will not overwrite a completed sealed private app.

You must supply **your own legally obtained local game files** to play/test:
- Crash Bandicoot (USA) supported **SCUS-94900** original CUE+BIN together, or supported CHD, in a folder you control.
- For later Mario sm64ex runtime, **your own** verified USA `.z64` ROM; `Build-Integration.ps1 -MarioRom <your local file>` checks the pinned US hash.
- Neither those games, private saved state, extracted assets, nor caches have ever been published as part of this repository.

On a system with working GPU OpenGL 4.3+, no software renderer should be necessary. If WGL/GL 4.3 is unavailable, first diagnose real GPU/driver support; consider **app-local** Mesa software GL (see `docs/WINDOWS.md`, verified 26.2.4 URL and SHA-256), placing `opengl32.dll` and `libgallium_wgl.dll` next to the **private compiled executable only**. Do not copy arbitrary DLLs, install unsupported system drivers, or upload Mesa DLLs to Git. Optionally set process-local `$env:GALLIUM_DRIVER='llvmpipe'`. Test a visible, responsive game window **before** interpreting absence of UDP packets.

Only after the private launcher is built, native dependencies resolve, a supported owned Crash disc exists, and the window can open, run the opt-in bounded diagnostic collector:

```powershell
cd crash-mario-fusion
$env:PATH = 'C:\msys64\mingw64\bin;' + $env:PATH
$disc = 'D:\MyGames\Crash\Crash Bandicoot (USA).cue' # replace with YOUR actual file
& 'C:\msys64\mingw64\bin\python.exe' -m tools.collect_crash_pose --crash-disc $disc --seconds 180 --count 1200
```

During actual Crash gameplay, stand, walk different directions, jump, pause ~5 seconds, resume and continue. The collector keeps logs under `%LOCALAPPDATA%\CrashMarioFusion\telemetry\crash-*`, ends within the bounded window, and stops its own child. If it fails with 0 packets, first check the private `crash.log`, the window state and start arguments rather than attempting calibration. All logs/ROMs remain local. Read the latest `docs/WINDOWS.md` before changing native behavior.

## What the Codex/new ChatGPT agent must do next

1. Read this handoff, `AGENTS.md`, `docs/CODEX_HANDOFF.md`, `docs/STATUS.md`, `docs/EVIDENCE.md`, `docs/CONTRACT.md`, `docs/DECISIONS.md`, `docs/WINDOWS.md`, `docs/M3_GEOMETRY_GATE.md`; inspect actual Git branch, `git status`, pinned sources and prior test results. **Do not restart M0/M2/M3 or recreate already implemented modules**.
2. Verify the new PC's prerequisites and rebuild private runtime and native fixtures. Keep original commercial user files private and outside Git.
3. Confirm a responsive original Crash window with OpenGL 4.3 or optional app-local trusted Mesa; diagnose any blocked/orphaned process separately. Verify a **fresh** original-game CMW1 Crash diagnostic capture with varying signed XYZ, native level/rotation, sequences, rate, pause and object lifecycle. No valid packet = NOT_VERIFIED.
4. Only afterward investigate a genuine native Crash post-physics callback/frame identity, shared landmarks and scale/yaw alignment. The diagnostic PadRead CMW1 phase 0 may not certify world collision. Never invent world-frame identity or insert live colliders without collision-source ownership and pool-capacity evidence.
5. Keep PR #2 draft and unmerged until true shared-world gates; push future code only into feature branches after verifying tests and obtaining user authorization. Source-only CI is not a substitute for native Windows gameplay.

## Privacy/portability classification

**GitHub has**: authored code, test harnesses, workflow scripts, pinned source revisions, engineering contracts, sanitized findings and this handoff.

**GitHub does not have**: purchased game files (CUE/BIN/CHD/Z64), private Windows `%LOCALAPPDATA%` caches, compiled game exes, Mesa app-local binaries, environment variables/secrets/session IDs, full private traces, saved games, or currently open process states. A clean clone is a reproducible *source* checkpoint, **not a ready-to-run installed game**.
