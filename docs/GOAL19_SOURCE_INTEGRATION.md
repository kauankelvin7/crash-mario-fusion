# GOAL #19 — Native input + original Crash source-observation integration

**Status: EXPERIMENTAL / NOT PLAYABLE.** GitHub acceptance issue: https://github.com/kauankelvin7/crash-mario-fusion/issues/19

Renderer continuation: `feat/goal19-native-renderer` adds a compiled, opt-in
GPU self-depth source contract and synthetic Windows pixel fixtures. No original
game clip-frame producer is connected; the existing ImGui fallback is unchanged.
This does not pass G1/G2 original-game fidelity or playability gates.
See `GOAL19_GPU_RENDERER.md` for the exact projection blocker and proofs.

This isolated integration worktree combines the independent source-only commits
`912c37a` (M4.3 native Mario control input) and `50e373c` (M4.2 original Crash collision-source diagnostic),
both based on the pinned camera-provenance work. It does **not** connect any original Crash collision
to Mario physics, remove the authored floor, or create shared world camera/depth. It preserves original branches,
source pins, native binaries and user-owned game data.

## Verification on Windows 11, 2026-10-10

- `C:/msys64/mingw64/bin/python.exe -m unittest discover -s tests -q` with the documented pinned
  `CM64_C1_ROOT`, `CM64_SM64EX_ROOT`, normalized git line endings, private temp directory:
  **162/162 PASS**. Source/reference/synthetic only; no original game spawned by these tests.
- `dotnet build tests/CrashOctree.Tests.csproj`: **0 warnings, 0 errors**;
  the compiled executable reports **27/27 synthetic collision decode checks PASS**.
- `dotnet build tests/m43_input/InputTests.csproj`: **0 warnings, 0 errors**;
  compiled test reports **17/17 source/input contract checks PASS**.
- `git diff --cached --check`: **PASS** before integration commit.
- The earlier M43 original-game `-CheckOnly` preflight passed for privately owned ROM/disc.
- Two separate bounded original Windows M43 native sessions were launched on the original game
  with the private opt-in live controls. Original game startup printed `INIT_OK`, the GPU atlas
  uploaded, and stderr was empty. A verified-PID/HWND-only operator could *not* acquire actual
  foreground focus (`SetForegroundWindow` refused), so no navigation/real control was accepted.
  **Native trace had zero completed Mario ticks in the first session; strict native gate FAILED.**
  Neither original-game session proved independent control, gameplay, shared collision, or visual depth.
  Do not report these trials as G4 passes. Failed operator helper stayed only under private AppData.

## Acceptance-gate truth

| Gate | Status |
|---|---|
| G1 original same-frame source camera/scene/depth | BLOCKED: raw camera variation only; no matched GTE vertex reprojection |
| G2 original Mario mesh/depth fidelity | PARTIAL: genuine mesh/UV atlas, ImGui overlay; no pixel-correct self-/scene depth |
| G3 authentic Crash-derived physics collisions | BLOCKED: raw octree diagnostic incomplete (native traversal limit, material/neighbor/lifetime unknown) |
| G4 independent Mario and Crash live controls | SOURCE-ONLY VERIFIED; ORIGINAL GAME BLOCKED by window-focus/operator validation |
| G5 shared physical object interaction | BLOCKED: no common actual Crash collision |
| G6 end-to-end original Windows gameplay reliability | BLOCKED: original session does not pass native playability gate |
| G7 original asset privacy | PRESERVED in this worktree; no retail ROM, disc, video, screenshot, native DLL or private trace in Git |

## Next engineering steps

1. Use a real interactive focused Crash window to operate the **already compiled** M43 gate; record
   native x/z displacement, input-caused jump/ascent/landing, and distinguish it from automated
   or authored-floor motion. If focus cannot be verified, fail closed and explicitly record it.
2. Derive native source-query and neighbor/scene generation provenance from original `ZoneQueryOctrees`;
   compare bounded original query results, semantics and material codes to c1, **not** entire
   overlarge octrees or authored terrain. Reject source allocations with unknown lifetimes.
3. Capture original GTE SXY/Z and camera from the **same source rendering frame** and verify
   actual retail-center depth/occlusion. Switch from authored ImGui screen positioning to a tested
   per-pixel 3D Mario renderer only after those coordinates agree.
4. After original-source matched scale/axes and real collision semantics, perform one bounded
   native Mario contact test with no authored floor. Only then verify interaction with the *same*
   original Crash object and repeat original-game operator tests.

**Do not merge into main, close #19, or label this playable.**
