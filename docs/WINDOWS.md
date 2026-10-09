# Windows 10/11 x64 local workflow

Native Windows status: **real local startup VERIFIED (2026-10-09)** with an optional app-local Mesa3D software OpenGL renderer. The passive paired runner starts both original/recompiled game processes and their separate windows. **Native Mario coin pickup and its receipt by the real Crash runtime are VERIFIED_REAL in passive mode; an applied jump/landing and shared-world gameplay remain NOT_TESTED. No playable fusion exists yet.**

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

## Keyboard-only one-shot jump validation

On the Windows machine with both legitimate game files already configured and the optional app-local Mesa OpenGL fallback, use:

```powershell
$env:GALLIUM_DRIVER = 'llvmpipe'
./tools/windows/Start-Integration.ps1 -CrashDisc "$HOME/Downloads/Crash Bandicoot (USA)/Crash Bandicoot (USA).cue" -Apply -KeyboardArm -Seconds 900
```

In Crash **gameplay** (not the title/menu), tap **W** once and release it. This corresponds to R1, and logs `[cm64] keyboard armed ... expires_in_ms=60000`; then move focus to Mario and collect one yellow coin within 60 seconds. The first valid event can issue one bounded native Cross pulse even after keyboard focus leaves Crash, without keeping W held. A second coin is observe-only until W is tapped again. Pausing with Start, changing Crash levels, or waiting past the expiry disables the pending authorization. Review Mario `coin seq=N`, Crash `received seq=N` and `input_applied seq=N`. The log `input_applied` is **not** proof of an actual jump; verify physical jump and landing visually before claiming gameplay success. Native Windows fixture tests: 21/21 pass. This mode requires both `-Apply` and `-KeyboardArm`; passive mode remains the default.

## Post-input Crash motion diagnostics (Windows)

After a valid real `input_applied seq=N`, the authored Crash source mod now **reads** (never writes) the original NTSC-U player object for 3.5 seconds. It records `motion_sample seq=N` every ~120 ms: raw Y position, vertical velocity, state index, AIR flag and GROUNDLAND flag. The closing `motion_summary seq=N` records min/max/last Y and `rise_and_landing_candidate`. Candidate means **observational evidence to review**, not an automatically validated physical jump: inspect the timeline and game window before calling it real. Invalid/unavailable player pointers, level changes and pauses stop sampling without changing input/physics. Original upstream fields are grounded in the pinned `RecompOne.Runtime/Host/FramePacing.cs` (Crash pointer `0x800566B4`, translation Y `+0x84`, velocity Y `+0xA8`, state `+0x2C`, state flags `+0x120`, status A `+0xC8`). This is a diagnostic specific to the supported US Crash build, not a universal memory map.

Use the keyboard-only `-Apply -KeyboardArm` command above. Tap W in real Crash gameplay, switch to Mario and collect a yellow coin within 60 seconds. Keep Crash unpaused and visible while it moves. Correlate `coin`, `received`, `input_applied`, `motion_sample`, `motion_summary` by sequence, and separately verify the visual jump/landing. As of this change, local Windows fixture checks **25/25 PASS**, Python **6/6 PASS**; the new native-state sampling has **not yet been observed in a live cross-game jump**, and shared-world fusion remains unimplemented.
# Next local test: M3 XYZ and calibrated frame preflight

M2 already passed on the user's Windows PC (CODEX_HANDOFF/EVIDENCE); older
NOT_TESTED notes below are historical. This increment has only Cloud synthetic
verification. In PowerShell 7, rebuild/install the updated source mod using
the existing configured private game files, then run:

```powershell
./tools/windows/Build-Integration.ps1
./tools/windows/Test-Integration.ps1  # expect 27 fixture checks
./tools/windows/Start-Integration.ps1 -CrashDisc 'D:/MyGames/Crash/game.cue' -Apply -KeyboardArm -Seconds 300
```

Use the previously validated keyboard procedure: W in unpaused Crash gameplay,
release, collect a Mario coin within 60 seconds. Inspect the private Crash log
under `%LOCALAPPDATA%/CrashMarioFusion/M0/logs`: `motion_sample` must now retain
Y/flags and add signed `x_raw`, `z_raw`, `crash_level`. Move Crash horizontally
while sampling to verify X/Z change; verify native controls/jump/landing remain
normal. The M3 reader itself injects nothing; this paired acquisition uses the
existing guarded M2 input. Do not upload local logs or game files.

Create an explicit calibration using local measured/chosen placement anchors,
not arbitrary defaults. Origin XYZ inputs are JSON arrays; Crash origin is
raw XYZ divided by 256, Mario origin is the native `received ... pos=` value.
Scale and yaw describe the chosen world placement, not measured physics units.
This prompt writes only operator-supplied values to the private cache:

```powershell
$calibration = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/world-calibration.json'
@{
    schema_version = 1
    crash_level = [int](Read-Host 'Crash level from motion_sample')
    mario_frame = Read-Host 'Confirmed Mario level and area (remain in this area)'
    crash_origin = @(ConvertFrom-Json (Read-Host 'Crash native origin [x,y,z], raw divided by 256'))
    mario_origin = @(ConvertFrom-Json (Read-Host 'Mario native origin [x,y,z]'))
    scale = [double](Read-Host 'Explicit positive landmark distance ratio Mario/Crash')
    yaw_degrees = [double](Read-Host 'Explicit XZ landmark alignment yaw in degrees')
} | ConvertTo-Json | Set-Content -LiteralPath $calibration -Encoding utf8
./tools/windows/Test-WorldCoordinates.ps1 -CrashLog 'C:/path/to/private/crash.log' -Calibration $calibration
```

Review `crash_native`, `mario_candidate`, `roundtrip_error` and
`floor_query_safe` in the private report. Test a new level against the old
calibration: it must fail. Old Y-only M2 logs must fail; do not invent XZ.
A true bounds flag does not assert a floor exists. Mario level/area is still
operator-confirmed, not instrumented. This test validates observations and
placement only: neither character walks on the other's geometry yet.
Next necessary work is verified native geometry/material extraction locally
and a native collision insertion seam with explicit world ownership.

## Asset-free native-code geometry oracle (no game launch)

From the configured Windows checkout in PowerShell 7:

```powershell
./tools/windows/Test-Geometry.ps1
```

This uses existing pinned public sm64ex source/MSYS2 GCC, authored triangle
data, bounded fixture pools and the original loader/floor queries, plus pure
geometry/snapshot tests. It neither reads ROM/disc files nor starts the games.
Linux Cloud ASan/UBSan results do not establish Windows sanitizer coverage.
The new script has only been parsed on Linux; actual Windows execution pending.
Log remains private in the standard TaskLogs directory.

The next **real** experiment requires explicit local execution authorization:
passively observe authentic Crash collision query bounds/type/subtype at the
existing physics/final-update seams, record level/zone/object generation and
validate source units separately from player XYZ. Observe Mario pool occupancy
and dynamic cleanup/update ordering in the selected area. Confirm calibration
and native motion visually. Do not inject even one replica until those gate
conditions pass; include a no-insertion control and reload cleanup when ready.

## M3 geometry oracle: native Windows validation (2026-10-09)

`Test-Geometry.ps1` now passes **17/17** on the configured Windows 11 / MSYS2 MINGW64 machine. The first local run exposed a PE/COFF linker portability difference: unused full-game dependencies retained by MinGW caused undefined references despite `--gc-sections`. The isolated test harness now supplies **Windows-only abort-on-call stubs** for those unrelated paths. It continues to compile and exercise the **original pinned** sm64ex surface loader and `find_floor`; if an unrelated stub is called, the test aborts instead of reporting a fabricated result. The complete Python suite passed **34/34**, and `Test-Integration.ps1` passed **27/27** using fixture RAM. These are synthetic results, not a real-world collision test. The original checkout and game processes were left untouched.

The real XYZ/calibration procedure above is still pending and requires a paired game session and operator-confirmed landmarks. Never use the authored synthetic oracle coordinates as live calibration anchors.

## M3.1 private native Mario pose capture (first half of two-engine telemetry)
Windows 11 x64: opt-in, rate-limited (at most 10 Hz), read-only **Mario** pose frames emitted from the post-update native gameplay seam. No Crash continuous pose emitter yet; M2 CMJ1 and existing Crash jump tests are independent. Native Mario level+area IDs and an observer-local epoch travel in the 16-byte CMW1 frame field; the epoch is NOT authoritative engine frame generation. The emitter invalidates its frame across pause/area changes and refuses unavailable states. Limit 300 seconds and 3000 samples per run, to UDP 127.0.0.1 only, with no network replay or gameplay modification. Logs and the authorized retail ROM stay in LOCALAPPDATA outside Git.

From the isolated project worktree in **PowerShell 7**, after a successful Build-Integration.ps1 (on your own cached validated Mario ROM):

```powershell
cd 'C:/Users/Kauan/Projects/crash-mario-fusion-m3'
$env:PATH = 'C:/msys64/mingw64/bin;' + $env:PATH
$env:GALLIUM_DRIVER = 'llvmpipe' # only on the verified Intel-HD local Mesa software-GL setup
$marioExe = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0/sm64ex-cm64/build/us_pc/sm64.us.f3dex2e.exe'
& 'C:/msys64/mingw64/bin/python.exe' -m tools.collect_pose --mario-exe $marioExe --seconds 90 --count 800
```

The collector launches exactly one Mario child with CM64_POSE_ENABLE=1 and a fresh random session, writes snapshots.jsonl/mario.log/summary.json into LOCALAPPDATA/CrashMarioFusion/telemetry/<random-folder>, and closes the child at timeout, count or Ctrl+C. This session has **not yet been run with the new emitter**; successful source/native compilation is NOT live-game proof. For a real gate the operator must move Mario while playing, confirm actual native level and area, pause/area transition behavior, and visually verify normal original gameplay. Never commit the retail files or telemetry. No calibration is automatic and no shared physics is implied. Original M2 session and runner remain separate.

## M3.1 Mario live-pose collector observed result — 2026-10-09
The user executed the prior documented 180-second private native Mario collector: 1,137 accepted CMW1 pose packets; zero rejected; original native player XYZ, Mario level=16 area=1, walking and jump action identifiers, original-game native ticks; no packet sequence losses and observed max 9 messages in a sliding 1-second interval. A 4.7-s silent gap coincided with an observer epoch change, compatible with the requested pause but not conclusive proof of pause suppression. All five observer epochs were in the same area, therefore an actual area switch was not tested. WASAPI audio endpoint warning did not prevent pose collection. Generated summary.json intentionally keeps calibration_ready=false and live_gameplay_verified=false as a collector-internal no-visual-certification default. Human review classified actual native CMW1 telemetry VERIFIED_REAL; cross-engine calibration remains BLOCKED. No telemetry bytes were put in source control.

## M3.2 — private real Crash diagnostic pose test (not Mario and not shared-world calibration)
Preflight already performed on user's Windows 11: Build-CrashPose.ps1 compiled a **separate** .NET 10 Crash launcher at LOCALAPPDATA/CrashMarioFusion/M3-crash-pose/app with 0 errors/warnings and SHA-256 manifest. It reuses the user's original retail Crash CUE *only at runtime*, locally; it does not upload, duplicate or mutate that disc. Original Crash M0 launcher and both main/m0-recon worktrees untouched. This diagnostic mod is disabled outside an operator-controlled session, and no new actual Crash gameplay session has yet been run.

From PowerShell in the isolated source checkout, run the one-shot collector below (it launches its private Crash, not Mario):
```powershell
cd 'C:\Users\Kauan\Projects\crash-mario-fusion-m3'
$env:PATH = 'C:\msys64\mingw64\bin;' + $env:PATH
$disc = Join-Path $HOME 'Downloads\Crash Bandicoot (USA)\Crash Bandicoot (USA).cue'
& 'C:\msys64\mingw64\bin\python.exe' -m tools.collect_crash_pose --crash-disc $disc --seconds 180 --count 1200
```
In actual Crash gameplay: stand still at first, walk different directions for >=15s, jump normally 3 times, pause ~5s then resume, walk+jump more, preferably change level only if convenient. The collector stops after at most 180s or 1200 accepted packets (Ctrl+C also stops it) and closes *only its child*. It requires the private sealed allowlisted build, sends/accepts localhost UDP only, and stores snapshots.jsonl, crash.log and summary.json in a random folder under LOCALAPPDATA/CrashMarioFusion/telemetry, never Git. If the runtime cannot reach valid gameplay or emits no packets, the collector exits with an honest failure and retains the private summary for diagnosis; don't retry blindly or delete game folders.
Expected validation: native signed XYZ and rotation variation, actual Crash level, observer epoch changes on pause/level/replacement, sequence order, <=10Hz and unchanged native input. The CMW1 phase is UNKNOWN_DIAGNOSTIC, native_tick is a pad-callback ordinal, and this run **cannot validate postphysics coherence or world-fusion alignment**. Do not ask for coins/W arm, Mario is NOT involved in this session. M2 integration is unchanged. For another Build-CrashPose, an existing sealed private directory is intentionally protected, so do not rerun the build script over it; use the collector with the already verified build.
# Reference-box checks without starting games

On the new Windows PC, after the migration handoff's Setup.ps1 prerequisites:

```powershell
./tools/windows/Test-ReferenceGeometry.ps1
```

The script fetches only pinned public c1 source if absent, preserves existing
cache changes, and executes five authored reference-boundary checks against
existing public sm64ex source. No ROM/disc or game process is used. Linux
ASan/UBSan and PowerShell parsing do not certify this new Windows script;
actual native execution remains NOT_TESTED until run locally.

## M3.3: paired receiver on the new PC (not yet executed on Windows)

Asset-free combined checks: PowerShell 7,
`./tools/windows/Test-ReferenceGeometry.ps1 -FullSuite` (both pinned public source
oracles; no retail files). `Test-OfflinePreflight.ps1` also includes new collector
and composition tests. Native MinGW Python for capture is separate from source
checks: if absent, install `mingw-w64-x86_64-python` with the existing MSYS2 package
manager. No new private native game build is claimed by these scripts.

Only when the operator chooses to run the original games locally, use **three
PowerShell terminals**. Do not run either old individual collector concurrently:
they bind their own ports, launch their own processes and timestamp different clocks.

1. From the repo, start the passive receiver. Substitute operator-declared expected
   native level/area/observer epochs; they are inputs, not automatically observed
   facts. Choose receipt-age/gap tolerances explicitly; do not interpret them as
   physical latency. These shell variables must be assigned before the call:

   ```powershell
   ./tools/windows/Start-PairedObservation.ps1 -CrashLevel $expectedCrashLevel -MarioLevel $expectedMarioLevel -MarioArea $expectedMarioArea -CrashEpoch $expectedCrashEpoch -MarioEpoch $expectedMarioEpoch -MaxAgeNs $receiptAgeLimitNs -MaxGapNs $receiptGapLimitNs -Port 39100 -Seconds 120
   ```

   The script prints the private JSON config path and `READY`. Copy **only that
   path** to the other terminals; wait for READY before starting emitters. The
   script creates independent fresh sessions and runs no game. Expect rejection
   until the declared frames match; a native startup/area transition can change
   the observer epoch. Inspect `observed.identity` and rejection/status rows
   locally rather than trusting a hardcoded epoch.

2. Mario terminal, from the repo, after inspecting the config:

   ```powershell
   $python = 'C:/msys64/mingw64/bin/python.exe'
   $env:PATH = 'C:/msys64/mingw64/bin;' + $env:PATH
   $cfg = Get-Content -Raw '<private-config-path>' | ConvertFrom-Json
   Get-ChildItem Env:CM64_* | Remove-Item
   $env:CM64_POSE_ENABLE = '1'
   $env:CM64_POSE_SESSION = $cfg.sources.mario.session
   $env:CM64_POSE_PORT = '39100'
   & '<existing-private-instrumented-Mario.exe>'
   ```

3. Crash terminal, from the repo, using the existing sealed diagnostic build and
   an owned local disc (no download or rebuild of retail data):

   ```powershell
   $python = 'C:/msys64/mingw64/bin/python.exe'
   $env:PATH = 'C:/msys64/mingw64/bin;' + $env:PATH
   $cfg = Get-Content -Raw '<private-config-path>' | ConvertFrom-Json
   Get-ChildItem Env:CM64_* | Remove-Item
   $env:CM64_CRASH_POSE_ENABLE = '1'
   $env:CM64_CRASH_POSE_SESSION = $cfg.sources.crash.session
   $env:CM64_CRASH_POSE_PORT = '39100'
   $exe = & $python -c 'from tools.collect_crash_pose import checked_launcher; print(checked_launcher())'
   if ($LASTEXITCODE -ne 0) { throw 'Diagnostic build validation failed.' }
   & $exe --run '<owned-private-Crash.cue>'
   ```

Observe original movement and mark pause/resume/level-area transitions manually.
Receiver stops at the time/packet budget or Ctrl+C; it does **not** terminate the
separately launched games. Close them yourself. Local `observations.jsonl` and
`summary.json` include sequence holes, receipt gap/age, independent identities,
rejection reasons and `source_delay=UNKNOWN`. Frames/gaps/pauses invalidate one
source; CLI never auto-rebinds. To recover, end the session and start a new
explicitly configured receiver **and both emitters with its new sessions**; API
users may instead perform a reviewed per-engine rebind. Do not edit config while
capture is active. Never upload these logs, session config, executables or discs.

This procedure is **NOT_TESTED on native Windows** for M3.3. Even comparable
observations leave physical status BLOCKED. Proven Crash postphysics ownership,
native frame generations, actual landmark correspondence and authentic geometry/
material/pool lifecycle evidence are still required before shared collisions.
