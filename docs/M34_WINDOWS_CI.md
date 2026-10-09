# M3.4 — Windows asset-free CI gate

This is a **source-only compatibility gate**, not gameplay integration. The base is M3.3 PR #7, `feat/m3-integration-observer` (commit `35b7cbf`). Existing public pins, game contracts and release restrictions remain unchanged.

The new workflow `.github/workflows/windows-native-source-checks.yml` runs on hosted Windows x64 when a PR targets `feat/m3-coordinate-contract`. It uses the documented MSYS2 MINGW64 toolchain (native Python and GCC), checks out pinned public `sm64ex` and `c1`, parses the existing Windows PowerShell scripts without executing them, and runs the complete `python -m unittest discover -s tests -v` suite. Python test modules compile and run their isolated original public-source C geometry oracles. No ROM, CUE/BIN, CHD, game executable, nonpublic assets or private telemetry are available in this runner.

The workflow also checks out pinned public RecompOne Crash launcher sources (Matteo842/CrashBandicoot-Launcher at `224da775`) and uses .NET SDK `10.0.401` to compile/run the original event-bus/RAM mod fixture harness. A successful harness run confirms only source-only C# adapter behavior under Windows. It does not build or start the private launcher and cannot read a commercial game.

**Evidence levels:**
- A successful Windows Actions run establishes **VERIFIED_SYNTHETIC (Windows x64)** for the source fixtures and confirms relevant tools compile/run on Windows. It does *not* establish VERIFIED_REAL.
- Linux ASan/UBSan results from PR #7 remain independent; the Windows GCC tests intentionally run without ASan/UBSan.
- The native mod's private `.NET` Crash launcher, real original game, actual OpenGL, pause/scene semantics, player pose, renderer, postphysics ordering, native pools, and shared world remain **NOT_TESTED/BLOCKED** until the operator tests the new PC.
- If Windows CI fails, record the exact runner log and repair only a demonstrable portability issue. Never silence failed fixture checks by adding skips, fabricating samples, disabling protections, or changing public source pins.

**Local reproduction on the user's new computer:** follow `docs/PC_MIGRATION_HANDOFF.md` setup and `docs/WINDOWS.md`; run `./tools/windows/Test-ReferenceGeometry.ps1 -FullSuite` and `./tools/windows/Test-OfflinePreflight.ps1`. Do not assume this workflow compiles or launches the two games. Never commit commercial files or transient private logs.

**Gate sequence for a truly playable fusion remains:** real Crash window/pose, real paired collector observations with one receiver clock, a provenance-confirmed postphysics read seam, corresponding operator-verified landmarks, source-native collision geometry/material/pool ownership, and finally one shared controllable world/rendering with verified collision behavior. M3.4 is a preparatory portability check and not evidence that those gates are complete.
