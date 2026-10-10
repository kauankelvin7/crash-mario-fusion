# M3.6 — operator-assisted original-runtime pose gate

**Status:** source-only workflow added. Original gameplay movement and native postphysics ownership remain NOT_VERIFIED; physical synchronization and collision remain BLOCKED.

M3.5 validated 88/88 source/native-oracle tests on the Windows x64 PC, 58 Crash fixture assertions, and 27 original C→Crash bridge checks. Both actual games launched with responsive OpenGL windows, but the finite Crash (90 s) and Mario (55 s) observations had zero accepted UDP packets without operator-confirmed in-level movement. This is neither a successful live pose capture nor evidence of a defective sender.

## Scope and procedure

The PowerShell 7 script tools/windows/Run-PoseGate.ps1 wraps the existing native collectors one game at a time. It verifies native MinGW64 Python, Crash's sealed private launcher or Mario's private instrumented executable, plus an explicitly operator-supplied local Crash disc. It does not synthesize game inputs, inject shared collision or distribute files. -CheckOnly verifies prerequisites without launching a game.

On the authorized Windows PC, from the project root, run:

```powershell
./tools/windows/Run-PoseGate.ps1 -Game Mario -CheckOnly
./tools/windows/Run-PoseGate.ps1 -Game Crash -CrashDisc 'D:/MyOwnedGames/Crash/game.cue' -CheckOnly

# Start each one separately when physically able to enter gameplay:
./tools/windows/Run-PoseGate.ps1 -Game Mario -Seconds 180
./tools/windows/Run-PoseGate.ps1 -Game Crash -CrashDisc 'D:/MyOwnedGames/Crash/game.cue' -Seconds 180
```

Replace the example Crash path with the real private local path. Enter a playable level; walk in several directions, jump, stop, pause briefly, unpause, and resume motion. Intro/menu/loading scenes often yield no packets. All capture data remains private under LOCALAPPDATA/CrashMarioFusion/telemetry. Do not upload files. Successful output POSE_OBSERVED certifies only that the receiver accepted one game's frames; a failure POSE_NOT_VERIFIED means inspect the local summary/logs. Either result does not validate shared physics. Finite limits: 30–300 s and 1–3000 accepted packets.

## Remaining engineering gates

- Crash observes PadReadEvent in UNKNOWN_DIAGNOSTIC phase only for identified gameplay level, valid player, unpaused input. Pinned upstream VSyncEvent reflects vblank timing, not proven native postphysics ownership.
- Mario observes a guarded post-update level update with active area/player and no pause/transition; unplayed menus may produce no valid frames.
- Each standalone collector uses its own session and receiver clock. No comparable cross-engine synchronization is claimed. To test paired receipt later, use Start-PairedObservation.ps1 with a single receiver after both standalone gates succeed.
- True geometry calibration needs operator-verified noncollinear corresponding landmarks and holdouts, real Crash postphysics/frame ownership, native material/geometry provenance and bounded Mario collision pool lifetime. Until then all shared collision and playable fusion claims remain BLOCKED.

Keep PR draft, the original collision solvers and game files untouched, and main unchanged.
