# Windows 10/11 x64 local workflow

Native Windows status: **NOT_TESTED**. Cloud Linux builds and collision/disc checks passed; they do not establish Windows gameplay. The current deliverable prepares original runtimes and native probes; no playable fusion exists yet.

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

## Native event adapter test (prepared, Windows NOT_TESTED)

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
