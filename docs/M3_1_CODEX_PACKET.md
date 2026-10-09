# M3.1 — Codex implementation packet (2026-10-09)

ROLE: You are the primary implementation engineer for kauankelvin7/crash-mario-fusion, on the isolated clean Windows Git worktree C:/Users/Kauan/Projects/crash-mario-fusion-m3, local branch feat/m3-local-validation, head 065d17c. A separate reviewer will validate your work. Work autonomously through source inspection, implementation and tests; do NOT stop at a plan.

MISSION: First small, reversible read-only **continuous native spatial telemetry** slice, allowing true future Crash-to-Mario frame calibration without inventing scale/yaw/landmarks. Existing M2 event integration, original native gameplay, and code/document contracts must survive.

MANDATORY BEFORE EDITING:
1. Inspect git status, current commit, AGENTS.md, docs/CODEX_HANDOFF.md, docs/STATUS.md, docs/CONTRACT.md, docs/DECISIONS.md, docs/M3_GEOMETRY_GATE.md, docs/ORCHESTRATION.md, exact relevant source and existing tests. Follow rules and evidence classification. No resets/cleaning or replacing user changes.
2. Inspect actual pinned CrashBandicoot-Launcher (.NET 10) and pinned sm64ex (C/MINGW) source as needed, but do not edit upstream/cached originals. Capture exact read-only safe sampling boundaries.
3. Reuse CMW1 snapshot contract in integration/world_snapshot.py if appropriate, avoiding competing incompatible protocols. Distinguish CMW1 prototype fixture coverage from actual live emitter behavior.

CONCRETE ENGINEERING DELIVERABLE — implement smallest testable M3.1 vertical slice:
A. Opt-in (disabled by default), rate-bounded (e.g. <=10 Hz), read-only pose observation for Crash AND Mario, preferably in existing M2 source integration adapters. Include native XYZ, relevant orientation/state/level or area/frame identity only when justified by inspected native sources, sequence and native clock, fresh explicit session/frame identity. No writing player memory, no changing input events, no collision or renderer changes. Must not replace/interfere with CMJ1 or assume clocks are synchronized. If a truthful native frame/area id is unavailable, explicit 'unknown' and gate calibration; NEVER synthesize a seemingly real ID.
B. Safe local collection/inspection workflow on Windows for snapshots: strictly localhost, finite/count/time-bounded, validated packets, no arbitrary file paths from untrusted network, privacy-first log location outside repository, explicit enable flags and startup/stop/cleanup. Prevent telemetry spamming output and ensure old tests unchanged. If implementing live CMW1 transport to both adapters would exceed safe scope, finish ONE complete working emitter + the other as explicit blocked/pending, but do not claim both complete.
C. Deterministic unit/fixture integration tests for serialization, sequencing, malformed/NaN inputs, stale sessions/frame transitions, pause/unavailable states, and rate gate. Add native compile/parser checks grounded in existing scripts where possible.
D. Update docs/STATUS.md, docs/EVIDENCE.md, docs/WINDOWS.md, docs/CODEX_HANDOFF.md with truthful native/synthetic boundaries and one executable user-run Windows test. Do not present simulated coordinates as native gameplay.
E. Run python -m unittest discover -s tests -v; Windows PowerShell scripts Test-Integration.ps1 and Test-Geometry.ps1 when feasible (PowerShell 7 exe in LOCALAPPDATA/CrashMarioFusion/tools/pwsh/pwsh.exe); inspect results. If fixtures require SM64EX_ROOT set to pinned public cache. Do not run retail game binaries automatically in this agent task; reviewer will arrange an authorized live validation later.

HARD LIMITS:
- Never commit/copy/upload retail ROM/CUE/BIN, generated commercial assets, private M0 logs, session tokens, secrets or user files. Keep code/tests/docs only; use .gitignore/cache.
- Do not touch main or m0-recon; do not merge, publish/Release, or push remote. Do not commit until reviewer inspects diff; leave edits staged or unstaged, with report. Never delete/reset unrelated files.
- Do not force final collision architecture. Crash octree volumes != Mario triangles; synthetic oracle is not shared geometry.
- Prefer minimal implementation to broad refactors. Tests should establish native source buildability but any unperformed live game test stays NOT_TESTED.
- Operate only inside isolated worktree for source edits. Avoid repeatedly asking user; provide a working increment, reporting precise blockers.

ACCEPTANCE REPORT: concise summary, files changed, actual commands and pass counts, exact runtime source seams/limits, native vs synthetic classification, next live calibration steps. No guessing, no green gate without evidence.
