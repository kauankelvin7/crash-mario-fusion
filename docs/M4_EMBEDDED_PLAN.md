# M4 — Embedded Mario inside Crash (engineering goal)

Status: **M4.0 original native-host solver verified on authorized Windows machine**; all later milestones remain gated. Branch `feat/m4-embedded-sm64-spike` is stacked on `feat/m38-operator-qa`. The separate unfinished M3.9 worktree is untouched.

## Goal

Build one genuinely playable Crash × Mario level in one host/rendered world while preserving original movement/physics, collision semantics, and eventually authored game events. Treat full-game behavior as distinct from a first Mario-character slice. No retroactive claim that a movement-only library reproduces every SM64 interaction. Keep the existing full-sm64ex and Crash M2/M3 observers and original event proof as independent regression oracles.

## Original-game and ABI evidence — 2026-10-09

- Source pins: Crash Launcher `224da7757920a817de2d9242416f657ab95782ea`; libsm64 `fd11813208272b4271d92bd92feb8f3fdbe61be5`. Compiled MSYS2 MinGW64 GCC 16.1 Windows x64 PE `sm64.dll` in private `LOCALAPPDATA/CrashMarioFusion/M4-embed`.
- Native C executable `integration/embedded_mario/embedded_probe.c` linked to the original libsm64 DLL; used only the already privately owned and SHA1-pinned SM64 US ROM and **two authored, upward-facing floor triangles**. Logged **180 Mario ticks; 180 geometry frames; 101 movement frames; travel 1509.448 native units**, exit 0. This did not run Crash.
- .NET 10 C# P/Invoke probe `Interop.cs` and `Probe.cs`: verified x64 struct sizes **surface 44; inputs 20; state 60; geometry buffers 40**; repeated same result in .NET (**180/180/101 frames, native travel 1509.448**), exit 0. No ROM is ever committed, copied into Git, uploaded or released.
- Dedicated **private copy** of the original Crash Windows Launcher from the **sealed M3 observer build**, with **one opt-in mod** `cm64-embedded-mario` and pinned `sm64.dll` next to its apphost. Host OpenGL 4.3 window stayed responsive. The first Roslyn mod attempt failed a C# unsafe pointer lifetime compile check; source was corrected to use `fixed` for the three managed fields, and the second private Windows original-game run passed: `[Mods] loaded 1/1 mod(s)`, `[cm64-embedded] INIT_OK in Crash process`, `HOST_SOLVER frames=180 mesh_frames=180 moving_frames=101 surface=AUTHORED_NOT_CRASH drawing=false physical_status=BLOCKED`. No stderr exceptions; process stopped after finite bound.
- The **Codex CLI** was invoked on Windows in `--sandbox read-only`, confirmed `gpt-6.1-sol`; it returned a review supporting a bounded embedded solver but warned about the native global state, thread affinity, lifecycle, renderer and missing full SM64 object behaviors. It did not edit files or execute games. Original-game tests were performed separately through the authorized desktop terminal.

## Reproducible operator run

PowerShell 7 (authorized Windows with existing pinned M0 and sealed M3 private original runtime):

```powershell
cd "$env:USERPROFILE\Desktop\Projetos\crash-mario-embed"
./tools/windows/Build-EmbeddedMario.ps1 -CheckOnly
./tools/windows/Build-EmbeddedMario.ps1
./tools/windows/Run-EmbeddedMario.ps1 -MarioRom 'D:\Owned\SM64\baserom.us.z64' -CrashDisc 'D:\Owned\Crash\game.cue' -CheckOnly
./tools/windows/Run-EmbeddedMario.ps1 -MarioRom 'D:\Owned\SM64\baserom.us.z64' -CrashDisc 'D:\Owned\Crash\game.cue' -Seconds 40
```

Replace example local paths with owned originals. Build keeps a separate copy of open-source/upstream-derived code and local runtime binaries in private AppData; it cannot replace M3's sealed diagnostic app. Run verifies exact original Crash binaries, libsm64 DLL and mod source hashes, private Mario ROM US SHA1, exact one active mod, and finite time budget. A hard fail never turns into an assumed playable gate. The experimental mod does not open, copy or alter the commercial Crash disc directly. Local logs and PII-bearing paths must **never** be uploaded to GitHub, Actions, PRs or releases.

## Integration gates and decisions

| Gate | Definition | Status |
|---|---|---|
| M4.0 | Original Mario movement/geometry solver runs inside genuine Crash Windows host without modifying Crash control/physics | **VERIFIED_REAL host + AUTHORED geometry** |
| M4.1 | Mario visible: **M4.1A separate debug preview VERIFIED_REAL; M4.1B1 original Mario triangles on actual Crash OutputPanel game image VERIFIED_REAL**, authored screen-space anchor; M4.1B2A original Mario UV/textures and M4.1B2B0 raw Crash camera source/variation VERIFIED_REAL; calibrated native shared-camera/depth-composited renderer M4.1B2B1 still **BLOCKED** | **PARTIAL** |
| M4.2 | Authentic Crash collision/source-volume ownership, identity and scene lifecycle measured; reviewed volumes mapped into native Mario surfaces preserving native Mario solver authority | **BLOCKED** |
| M4.3 | Both playable native characters and shared physical object interactions, one world/renderer, repeatable ground-jump-landing and collision regressions | **BLOCKED** |
| M4.4 | Full original SM64 object/events, warps, HUD, enemies and Crash behaviors preserved in chosen hybrid architecture, then Windows release checks | **BLOCKED** |

The M4.0 mod ticks Mario on a bounded host `VSyncEvent` with a host-clock 30 Hz guard; VSync is **not** a proved Crash postphysics seam. Mario is visible both in a **separate diagnostic window** (M4.1A) and **directly over the original Crash displayed image** (M4.1B1). Neither version uses a calibrated Crash camera/depth nor authentic Crash collision; the original Mario collision surface is AUTHORED, not Sanity Beach. Mario's interaction `interact_noop` in the pinned libsm64 deliberately omits full-game interactions. The original Crash physics, memory and `PadReadEvent` remain untouched. DLL and caller are not asserted thread-safe; initialize and tick only on the same callback path. Game-frame ownership, cross-world calibration, Crash level mesh/volume material equivalence and full-render depth remain unsolved.

## Stop conditions

Never import all Crash retail or Mario ROM bytes into Git. Never substitute render triangles for verified physics volumes. Never claim shared surfaces/interactions based on one synthesized floor. Never merge this experiment into `main` without real native co-render and collision gates.
