# M4.3 independent Mario input — 2026-10-10

Branch: `feat/m43-independent-mario-controls`. No M4.2 worktree, original
binaries, earlier private runtime cache, main, retail data or branch history
is modified. No game process was launched in this task.

## Contract and source gate

- Opt-in `CM64_LIVE_CONTROLS=1`, plus existing `CM64_EMBED_ENABLE=1` and
  `CM64_INOUTPUT=1`. Without the live flag, the previous finite 180-tick scripted
  smoke path and result strings remain; historical real-game results are not
  a new regression run.
- Pinned Crash source `224da7757920a817de2d9242416f657ab95782ea` passed
  `python -m tools.m43_live_gate --source <M0 public checkout>`.
  `HostWindow.OnRender` updates ImGui before `PanelManager.DrawPanels`;
  `OutputPanel.DrawImage` owns the original image. Input capture executes only
  from that original overlay callback, never from VSync or global async keys.
- Original defaults: arrows move; Z/X/A/S face buttons; Q/W/E/R shoulders;
  F/G stick buttons; Enter Start; **ShiftRight Select**. Therefore RightShift
  is rejected. Mario uses **I/J/K/L** and **U jump**. Both configured Crash
  keyboard pads and configurable cheat hotkey are checked every UI sample;
  unknown/conflicting names fail closed. Crash bindings and pad state are not
  consumed, suppressed, reassigned or written.
- The private host adds only `OriginalMarioInputHost.InputAllowed`, exposing
  original foreground/focus and host pause-menu state. Missing seam disables
  live startup. `prepare_m43_host.py` validates the public pin and private
  original atlas/output source patches before generating this helper.
- Read-only PadRead scene observation uses pinned public Catalog level address
  `0x80056710` and FramePacing pause addresses `0x80056400`/`0x8005640C`.
  Unknown/non-gameplay levels, pause and stale observations are invalid.
  This callback is **not certified postphysics** and does not read Mario keys
  or change Crash RAM/PadRead. Level/validity transitions increment an epoch.
- One immutable latest snapshot, atomic publication, monotonic sequence,
  250ms leases; normalized diagonal movement and a cumulative bounded jump
  edge preserve quick taps. Focus/scene loss requires key release before
  reacquisition. No queue grows. Native calls remain serialized on their
  VSync owner thread; a rational 30Hz deadline never runs a catch-up loop.
- Native actor resets on scene epoch changes or authored-floor escape.
  Shutdown detaches callbacks and releases native buffers on the original
  owner. Wrong-thread native shutdown fails closed and defers allocation
  release to process exit, which the native operator gate rejects.
- At most 3600 live ticks. Private CreateNew JSONL records actual native
  X/Y/Z, velocities/action, host frame, input sequence, scene/actor epochs and clock for
  each executed tick. No scripted movement count certifies live control.
- Live mesh uses a fixed **authored** projection rather than recentering each
  frame, so native translation/jump remain visible. A labeled wire floor is
  authored debug geometry, not extracted Crash collision or a shared camera.

## Proof and unpassed gates

Windows .NET 10 compiled the isolated pinned host and typed mod in
`%LOCALAPPDATA%\CrashMarioFusion\M43-input`. No native Mario gameplay calls
or graphics were executed. The upstream host emits existing warnings;
the typed mod compiles separately. Asset-free Python and executable C#
contract tests cover gating, cadence, atomic snapshots, movement axes,
release/reset and short jump taps. These are **VERIFIED_SYNTHETIC** only.

Executed proofs: `python -m unittest discover -s tests` (144 tests, five
environment-dependent skips); .NET 10 `tests/m43_input/InputTests.csproj`
(17 executable assertions, no native DLL calls); and
`Build-LiveMarioControls.ps1` (isolated host + typed mod, exit 0).
SDK: .NET 10.0.401; Python 3.14.5; PowerShell 7.6.6. PowerShell parsing and
`git diff --check` also passed. Outputs/intermediates are under M43-input.
Final incremental host/mod builds
have zero warnings/errors; the initial full upstream build had six existing
warnings. `Test-LiveMarioControls.ps1` is supplied but **not executed**.

Human key delivery through the actual GLFW/WinForms focus path, independent
Crash steering, live visual movement, jump/land, pause/reload and safe
native unload remain **NOT_TESTED**. Authentic Crash collision, calibrated
camera/depth and physical interaction with Crash objects remain **BLOCKED**.

## Private operator gate and rollback

PowerShell 7; only owned local paths, no uploads:

```powershell
./tools/windows/Build-LiveMarioControls.ps1 -CheckOnly
./tools/windows/Build-LiveMarioControls.ps1
./tools/windows/Test-LiveMarioControls.ps1 -MarioRom 'D:\Owned\baserom.us.z64' -CrashDisc 'D:\Owned\Crash.cue' -CheckOnly
./tools/windows/Test-LiveMarioControls.ps1 -MarioRom 'D:\Owned\baserom.us.z64' -CrashDisc 'D:\Owned\Crash.cue' -Seconds 90 -ApproveHumanRun
```

Before the last command, coordinate with the M4.2 operator: **no other game
may start during this window**. The harness refuses an existing Crash process
and uses `Local\CrashMarioFusion-OriginalGame`; other workstreams must honor
the same lock or coordinate manually (process detection alone is not an
inter-workstream atomic reservation). It never stops another process.

Enter a gameplay level using original Crash inputs, click its image, release
Mario keys, then move both horizontal axes, jump from rest and land. Separately
steer Crash while Mario moves; verify pause, alt-tab and scene reload manually.
The original window is intentionally visible only for this approved human run.
The runner closes only its own PID after the bound and retains logs/JSONL in
M43-input. It checks seals, host responsiveness, actual native mesh presentation,
displacement on both axes, input-caused jump/ascent/landing, monotonic ticks and
30Hz average cadence. A spawn fall, epoch reset, empty trace or old smoke count
cannot pass. JSONL alone does **not** certify human independence or visuals.

Rebuild refuses private user edits by checking the previous seal first. All
generated host/source/compile/app files remain in M43-input. Rollback: close
the M43 process, unset the live flag (finite smoke) or launch the unchanged
original app; no file replacement outside M43-input is necessary.

## M4.2 integration next

1. Review this branch without merging or pushing; execute the authorized human
   authored-floor gate and review private evidence before calling it playable.
2. Exchange source contracts with `feat/m42-authentic-crash-surfaces`, not
   caches or commercial files. Keep this snapshot/cadence owner; feed reviewed
   surfaces to the existing native solver only at a jointly owned scene epoch.
3. Use one designated integration writer after reviewing both branch diffs.
   Replace the authored floor only after M4.2's authentic collider identity,
   units/materials and lifecycle gates pass. Rerun displacement/jump/landing
   and original Crash steering in the combined private host.
4. Shared camera, depth and object interactions require separate gates. Neither
   this authored renderer nor passing synthetic tests completes GOAL #14.
