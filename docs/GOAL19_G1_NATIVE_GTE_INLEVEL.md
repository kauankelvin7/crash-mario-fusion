# GOAL #19 — original Sanity Beach GTE/OT source capture

Date: 2026-10-10. Branch `feat/goal19-world-gte-inlevel`. Source-only stage; **NOT PLAYABLE**.

## Original Windows result

An authorized, time-limited original Windows Crash Bandicoot 1 execution entered Sanity Beach (original level 9) by requesting the existing pinned original host's developer-menu warp `CheatManager.RequestWarp(9,1)`. It was explicitly opt-in via `-WarpSanityBeach` and scoped to a private, ignored original-game runner. No synthetic input, guessed controller events, authored geometry or ROM/disc files were published.

Unlike the earlier title-screen-only game trials, the original guest `GfxTransformWorlds` method actually executed. An isolated, source-only mod hooked **original recompiled method 0x80019508** by `HookManager.AddPre/AddPost`, preserving execution and RAM. This bypasses a previous false assumption that the world routine necessarily travels through `Dispatcher.Call`.

The pinned c1 PSX assembly `src/psx/r3000a.s` `RGpuResetOT` initializes the **original ordering table with 2,047 forward 24-bit tags and exactly one 0xFFFFFF terminator**. The real Windows game confirmed that exact pattern at the guest world call, with a 2,048-word OT, rather than the previously assumed DMA6 ClearOTagR callback. `CrashWorldSourceProbe.OriginalGuestOtReset` now validates **all** 2,048 words and binds the original host's draw count and OT pointer before accepting a candidate, rejecting unknown or incomplete tables; DMA6 semantics remain supported where genuinely present.

**VERIFIED_REAL (original-game source observations):** the original game produced **24 source-owned GTE RTPT/world/OT receipts** before the bounded 24-record cap. The independent source-only auditor found **0 integer pixel errors, 0 original GTE Z errors**, full source/neighbor/polygon/pinned camera state checks, and 72 decoded original source vertices. Its exact classification is `RECORDED_G1_CANDIDATE_ONLY`, `self_consistent=true`, `run_authenticity_verified=false` because the generic JSON auditor alone cannot authenticate a private game; separate Windows runner validated sealed disc/game binaries, game PID, source runtime hash, responsiveness and teardown. Original runner output: `G1_ORIGINAL_ATTEMPT candidate=True pid_stopped=true input_sent=false` with `camera_calibrated=false`, `depth_complete=false`, `collision_ready=false`, `postphysics=false`. The private log/ROM/disc are under ignored `.cache/m42-g1/original-...` on the authorized Windows computer, **not GitHub**.

Independent C# GTE fixtures remain **VERIFIED_SYNTHETIC**: 3 positive (including rotated and GT3), 20 negative/opt-out; plus a newly tested native fixture scenario `guest-ot` exercises the true source-owned ascending OT chain without a DMA6 callback and returns one complete `GUEST_WORLD_RTPT_OT` record while preserving native memory/GTE registers. No artificial physics surface has been inserted.

## Still required before completion

- The 24 receipts establish original game GTE SXY/Z geometry and OT correlation for inspected samples, **not the full retail-centre depth buffer or camera-calibrated Mario clip producer**. The Mario self-depth GPU FBO (PR #22) still needs same-frame projection/compositing.
- Collision source query (separate `feat/goal19-native-level-proof`) has one authentic level-9 read-only 54-result query/52 compact nodes but **not** material semantics, allocation lifetime, dynamic object contact or a safe libsm64 solver surface.
- No independently controlled native Mario in actual scene, no shared physical object interaction, and no accepted end-to-end gameplay. Gates G2–G6 and final G1 scene completeness are **not passed**.
- Keep all source pins, original commercial assets and private observations local, issue #19 open, PR draft, main unchanged.

To reproduce the private GTE test on the authorized Windows machine, with the existing locally owned Crash disc:

```powershell
& pwsh -NoProfile -File tools/windows/Build-WorldSourceProbe.ps1
$disc = (Get-Content "$env:LOCALAPPDATA/CrashMarioFusion/M3-crash-pose/app/settings.json" -Raw | ConvertFrom-Json).CdPath
& pwsh -NoProfile -File tools/windows/Run-WorldSourceProbe.ps1 -CrashDisc $disc -Seconds 42 -WarpSanityBeach
```

The actual original-game runner may still fail closed, and should not be interpreted as proof of Mario playability.
