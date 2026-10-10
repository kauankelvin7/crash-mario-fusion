# GOAL #19 — bounded original GTE visible-operator attempt

**2026-10-10. Experimental only; NOT PLAYABLE. G1 remains BLOCKED.**

This separate worktree extends the existing reviewed world/GTE/OT probe with an **explicit opt-in visible original-game window** via `Run-WorldSourceProbe.ps1 -VisibleOperatorWindow`. Default is still a hidden, non-interactive original Windows diagnostic. The runner keeps exact source/guest binary hash seals, the user-owned disc solely under private LOCALAPPDATA, original mods disabled, bounded 15–80 second process lifetime, temporary private game app, receipt auditor, hard kill/exit, and fail-closed semantics. It does not send keys. With a visible window, the input status is recorded as **unknown/null** rather than falsely `false`, because a separately authorized and PID-scoped operator could act outside the runner. The regression tests now explicitly verify the conditional window mode, original no-input default and scene-probe privacy constraints.

## Verification and blocker

- Exact public source pin and private owned disc preflight: **PASS**.
- Private runtime built on native Windows .NET 10.0.401, **0 build errors** (six pre-existing upstream warnings), three positive GTE reprojection fixtures and 20 negative/disabled cases passed; synthetic auditor measured **zero integer pixel/Z error** for fixture vertices. This is **VERIFIED_SYNTHETIC**, not retail-game projection proof.
- Full reference Python suite in this worktree: **161/161 PASS** after updated regression.
- Original Crash game was started with visible window for a **70-second bounded attempt**. Three separately invoked, original-PID/HWND-scoped safe Enter inputs were **REFUSED** because the target was not foreground; no global input was sent. Native world auditor returned **REJECTED / No source-owned original RTPT/OT receipts**. The runner stopped the original process; captured owned runtime logs are retained privately.
- Consequently **no original in-level GTE camera/depth calibration, original scene ownership, original contact, Mario surface insertion or playable game** has been certified. The prior real native Crash level-9 original query hook, observed in the separate original-query worktree, remains the distinct first real-query-call result (`QUERY_SENTINEL` rejected), not a positive GTE receipt.

Follow-up acceptance requires actual source-owned in-level RTPT/OT observation from the original Crash game in the same frame as the active scene, original collider provenance and native successful guest Mario control, physical interaction, rendering and reliability. Do not relax source validations, modify original media or claim success based on keyboard-send attempts.

[Parent acceptance issue #19](https://github.com/kauankelvin7/crash-mario-fusion/issues/19) remains OPEN. Preserve all existing branch work, keep this as draft.
