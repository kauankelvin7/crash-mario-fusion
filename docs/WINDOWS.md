# Windows 10/11 x64 local workflow

Native Windows status: **real local startup VERIFIED (2026-10-09)** with an optional app-local Mesa3D software OpenGL renderer. The passive paired runner starts both original/recompiled game processes and their separate windows. **Coin pickup, cross-game jump/landing and shared-world gameplay remain NOT_TESTED; no playable fusion exists yet.**

Install Git, PowerShell 7 and official [MSYS2](https://www.msys2.org/). Finish MSYS2's documented update procedure before setup. Scripts use its MINGW64 x64 toolchain, and install .NET SDK 10.0.401 in `%LOCALAPPDATA%/CrashMarioFusion/M0`. Source/data/build caches and logs stay outside project Git. Existing source changes or wrong pins stop setup; no resets or replacement of user files.

From project root in PowerShell 7:

```powershell
./tools/windows/Setup.ps1
./tools/windows/Build.ps1
./tools/windows/Test.ps1
# Optional upstream synthetic codec suite with official MAME chdman.exe:
./tools/windows/Test.ps1 -Chdman 'C:/Tools/MAME/chdman.exe'
```

`-MsysRoot` supports a nondefault MSYS2 installation. Setup/build/test require no game data for Launcher + libsm64. Full Mario runtime needs your own big-endian US ROM; Build verifies the pinned upstream SHA1 before copying into the private cache. It never downloads retail data. libsm64 itself is only the collision/API probe candidate; full sm64ex preserves the object/event systems.

```powershell
./tools/windows/Build.ps1 -MarioRom 'D:/MyGames/SM64/baserom.us.z64'
./tools/windows/Start.ps1 -Game Crash -CrashDisc 'D:/MyGames/Crash/game.cue'
./tools/windows/Start.ps1 -Game Mario
# Startup-only Crash diagnostic, insufficient to prove gameplay/graphics:
./tools/windows/Start.ps1 -Game Crash -CrashDisc 'D:/MyGames/Crash/game.chd' -Smoke
```

Crash requires an owned supported NTSC-U SCUS-94900 CUE/BIN or CHD; its existing validator/recompilation pipeline handles the dump. Recompiled code/assets stay local. sm64ex uses its current OpenGL backend; Crash retains upstream OpenGL (4.3 context needed). Do not upload dumps or extracted assets into Cloud or commit/distribute generated runtime packages containing them.

Every command checks exit status and saves logs under the private cache. Tests prove only the scenarios they execute. `Start` writes an observation.json with gameplay/graphics/shared_event **NOT_TESTED**: upstream Crash smoke considers a 12-second running process sufficient, which is not our gameplay oracle.

Local validation procedure: run the synthetic tests; start each native runtime; verify normal movement/jump/landing, pause/resume and level load. For Mario, collect one ordinary yellow coin and record count/healing/object deletion. Save logs and actual captures privately with source revision, GPU/driver and scenario. In M1 compare that baseline with passive native-event instrumentation and identify Crash logical ticks independently of presentation. Only reviewed real runtime evidence may become VERIFIED_REAL. A targeted adapter check is implemented below; real shared-event gameplay and playable fusion remain unverified.

## Native event adapter test (native startup tested; gameplay interaction NOT_TESTED)

M0 sources are reused. The following prepares a private instrumented sm64ex copy; the original source checkout is untouched. Crash's source mod is installed beside the **apphost executable**, with existing settings/mods preserved and a settings backup. Use a controller for Crash's R1 gate and Mario's normal controls for the pickup; background focus/input behavior must be checked locally.

```powershell
./tools/windows/Setup.ps1
./tools/windows/Build-Integration.ps1 -MarioRom 'D:/MyGames/SM64/baserom.us.z64'
./tools/windows/Test-Integration.ps1
# First compare passive instrumentation with original gameplay:
./tools/windows/Start-Integration.ps1 -CrashDisc 'D:/MyGames/Crash/game.cue'
# Then enter both playable levels, hold Crash R1 while unpaused, collect one yellow coin:
./tools/windows/Start-Integration.ps1 -CrashDisc 'D:/MyGames/Crash/game.cue' -Apply -Seconds 300
```

Logs/run.json are private under `%LOCALAPPDATA%/CrashMarioFusion/M0/logs`. Correlate Mario `coin seq=N`, Crash `received seq=N`, and (only in armed apply mode) `input_applied seq=N`. Record actual Crash jump/landing and Mario's unchanged pickup consequences with Windows/GPU/driver metadata. Release R1 in pause/loading/death; native pause/grounded-state detection is not yet instrumented. A pulse may not produce a jump if Crash is airborne or blocked. Neither the runner nor synthetic tests certify gameplay. Two windows, separate worlds and cameras remain; this is not the final playable fusion.

Uninstall: disable `cm64-coin-jump` in the Launcher Mods UI (or restore the matching settings backup after reviewing intervening edits); remove only its source-mod directory. The original uninstrumented sm64ex remains in the M0 cache. To compare the same instrumented Mario executable without emission, run it with CM64_SESSION/CM64_PORT unset. No game data is bundled in a distribution.

Final distribution requirement recorded: once genuinely playable and validated on Windows, supply Release launcher + permitted dependencies, local owned-file import, ZIP and GitHub Actions packaging, then GitHub Releases with publication authorization. No installer/release package is being built ahead of that gate.

## Windows test results and OpenGL fallback (2026-10-09)

On a Windows 11 host with Intel HD Graphics driver 9.17.10.4459, native OpenGL initialization failed: Mario crashed at `gfx_opengl_init` (`0xC0000005`), and Crash reported insufficient WGL/OpenGL 4.3 support. The test installed **application-local** software GL, not a system display driver, using the verified [Mesa 26.2.4 Windows MSVC x64 release](https://github.com/pal1000/mesa-dist-win/releases/tag/26.2.4). Verified download SHA-256: `351fc8c8b695878ffb3eaa044b3ead08672a48b1a045e3c3e3975811df0f6695`. Its `x64/opengl32.dll` and `x64/libgallium_wgl.dll` were copied only beside **each compiled executable**. An optional process-local `GALLIUM_DRIVER=llvmpipe` enables the software path; no Windows global DLL, registry, or graphics-driver changes are required. This is a diagnostic fallback; it may be slow. Do not include Mesa distribution or commercial game data in project Git.

The verified native Mario binary is `sm64ex-cm64/build/us_pc/sm64.us.f3dex2e.exe`. The build must use `WINDOWS_BUILD=1 HOST_OS=Windows`, or the MSYS2 environment can incorrectly link with Linux `-lGL -ldl`. With private Mesa, Mario stayed alive with a responsive window for a 9-second startup check. Crash's original NTSC-U disc passed identification/recompile and reported `[Host] OpenGL window ready`. Its mod reported `[cm64] receiver ready`. On Windows, `Test-Integration.ps1` passed all 14 fixture tests; project Python tests passed 6/6. The passive paired runner exited normally after 45 seconds with both processes started and both windows responding. **No real coin pickup event was observed, no automatic jump was proven and no shared-world result is claimed.** Both apps reported a missing WASAPI audio endpoint in this remote session; audio and graphical gameplay are not verified. Logs are private under `%LOCALAPPDATA%/CrashMarioFusion/M0/logs` and `mesa-soft/`.

For a real manual event check, enter an actual playable level in both windows, hold Crash R1 during unpaused gameplay, and collect one yellow coin in Mario. First run without `-Apply` to inspect `coin seq=` and `received seq=` without injecting input; then repeat with `-Apply` and observe the real jump **and landing**. Do not treat `[cm64] input_applied` as proof of a native jump. If either step fails, preserve local logs and diagnose that exact failure instead of advancing the shared-world claims.
