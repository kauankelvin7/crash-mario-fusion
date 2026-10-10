# GOAL #19 — original native Crash query receipts (diagnostic, NOT contact)

Date: 2026-10-10. Worktree: `feat/goal19-authentic-contact`. Parent: [GOAL #19](https://github.com/kauankelvin7/crash-mario-fusion/issues/19). **BLOCKED / NOT PLAYABLE**.

## Implemented

This source-only increment adds opt-in, bounded original `ZoneQueryOctrees`/ `NSLookup` observation, using the exact pinned public c1 source rather than a guessed mesh or authored floor. It captures current-zone and neighbor identities, signed native query bounds, compact result descriptors/nodes and scene/thread/epoch provenance. Mutations of original RAM, post-physics claims, allocation-generation assumptions, per-material mapping, converted Mario triangles and libsm64 collider insertion are **explicitly forbidden**. `SurfacesAllowed=false` is invariant; no shared-world physics is enabled.

The private mod is `CM64_NATIVE_QUERY_PROBE=1`, bounded to at most 96 attempts/24 receipts/8 rejects/90 seconds, rejects unpaired or stale ownership, and only observes original functions. A separate original-game runner validates sealed public pins and original host binary hashes, isolates assets in `LOCALAPPDATA`, has a 25–90 second budget, enforces one original Crash process, writes private logs and always returns nonzero as long as gameplay is unproven.

## Verified now on authorized Windows

- Public c1 exact pin `256fdcef59f15a190290cc19db3fa9a707843b69` and private original host seals passed preflight.
- Full asset-free Python suite **170 tests PASS** (one optional .NET cross-check skipped on that run); focused original c1 C oracle **8/8 PASS** when the C# cross-check is enabled.
- `dotnet run --project tests/native_query/QueryTests.csproj -c Release`: **48 C# assertions PASS**. Public original C `ZoneQueryOctrees` fixture output was matched to the .NET receipt decoder (both mode 0 and mode 2), not only hard-coded JSON fixtures.
- `dotnet build integration/crash_collision/NativeQueryCompile.csproj -c Release -p:CM64HostDirectory=<private sealed host>`: **0 warnings/0 errors**.
- Private build and run preflight PASS. Original host: **25-second bounded run**, OpenGL window created, 1/1 diagnostic mod loaded, process responsive, and process stopped by runner. The private receipt audit returned **0 native query receipts** and `NO_ORIGINAL_QUERY_RECEIPTS`, exit 2. This is **real-game startup only**, **NOT in-level collision proof**. Do not convert a loaded hook into surface permission.
- Portable official .NET SDK 10.0.401 was installed under ignored `LOCALAPPDATA/CrashMarioFusion/toolchain/dotnet`, leaving the global Windows SDK installation unchanged. No retail media or logs included in Git.

## Blockers and safe next gate

1. Start the authentic original level under normal interactive focus and collect original in-level native query/neighbor/scene receipts. The short startup run produced none; never silently skip that prerequisite.
2. Prove allocation generation, frame/epoch and collision material/contact semantics before mapping any original Crash query node into guest Mario `Surface` triangles. Raw octree occupancy is **not** automatically a floor or gameplay material.
3. Match actual GTE rendering epoch and clip/depth against the original GPU renderer seam on PR #22; prove independent native controls, one common object and complete Windows gameplay. Do not merge this diagnostic into the playable game based on fixture counts alone.

The Windows CI now checks the native C-to-.NET query bridge using only public source. No original ROM/disc, game executables, captures or logs are committed, and original pins remain untouched.

**Acceptance: G1/G2/G3/G4/G5/G6 NOT PASSED; G7 asset privacy preserved. Main unchanged, issue #19 open.**
