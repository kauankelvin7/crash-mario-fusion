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

Local validation procedure: run the synthetic tests; start each native runtime; verify normal movement/jump/landing, pause/resume and level load. For Mario, collect one ordinary yellow coin and record count/healing/object deletion. Save logs and actual captures privately with source revision, GPU/driver and scenario. In M1 compare that baseline with passive native-event instrumentation and identify Crash logical ticks independently of presentation. Only reviewed real runtime evidence may become VERIFIED_REAL. No shared-event or playable-fusion check is implemented yet; D002 defines the next narrow interaction.
