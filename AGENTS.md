# Crash × Mario 64 — persistent Codex instructions

Mission: establish a **real cross-engine gameplay** fusion between Crash Bandicoot 1 (PS1, 1996) and Super Mario 64 (N64, 1996), prioritizing preservation of original movement, physics, events and object behavior.

## Current continuation (2026-10-09)

Read **`docs/CODEX_HANDOFF.md` first** when resuming on `m0-recon`. M2 original-game coin-to-Crash jump is VERIFIED_REAL on Windows with recorded native telemetry and the user's visual confirmation. Source-only Cloud tests and an asset-free GitHub Actions workflow have been added; **they do not rerun commercial games**. Work toward the first testable M3 shared-world increment, without uploading ROMs/PS1 disc data, restarting M0/M1/M2, treating recorded telemetry as a fresh run, or merging `main` automatically. The latest sections of `docs/STATUS.md` supersede its old historical M0 flags.

## Primary platform

Windows 10/11 x64 is the user's execution, graphics-test and distribution platform. Codex Cloud may run Linux; record cloud and native Windows results separately. Preserve the current architecture and milestones when adapting platforms. Prefer compatible native Windows toolchains (.NET, MSYS2/MinGW, MSVC/CMake where actually supported), keep upstream renderers, and provide PowerShell setup/build/test/start instructions. Do not claim Windows support without actual native compilation and execution. Owned-data/graphics validation runs locally on Windows; never fetch or upload retail files. Keep simple cross-platform probes; no RAM benchmarks or platform-triggered Astra calls.

## Operating rules

1. Start by checking `docs/STATUS.md`, `docs/ORCHESTRATION.md`, `docs/DECISIONS.md` and the current Git tree. Continue the next incomplete milestone, never restart it.
2. Consult upstream Universal Modder's **current** `skills/mashup-mods/SKILL.md`, appropriate references and documented oracles. Verify file paths before reading; do not follow nonexistent paths from old prompts.
3. Observe actual code and build systems before choosing between dual-process passthrough, embedded simulation or a hybrid. Do not hard-code IPC as the winner.
4. Only use the user's lawfully obtained game files in a local, ignored location. Do not download/distribute ROMs, include commercial code/assets in commits, bypass copy protection or touch online game services. The repo should contain source, converters and tests only as appropriate.
5. Do not benchmark RAM or optimize for the user's previously described 4 GB machine. This task targets Codex Cloud; only profile when a measurable, relevant issue arises.
6. Separate VERIFIED_REAL (instrumented real game runtime), VERIFIED_SYNTHETIC (fixture/mock), NOT_TESTED and BLOCKED. Never call mocks a real fusion. Record exact commands, versions, commits and logs.
7. Use short read ranges and code searches; do not dump entire upstream trees. Pick the cheapest mechanical oracle for each change, using ≤3 equivalent retries on a persistent failure.
8. Avoid decorative documents, generated art, music, video, FAL API or asset workflows at M0. Do not build two independent engines from scratch unless evidence forces it.
9. Only one agent writes shared integration files. Read-only investigations may run in parallel. Commit small tested changes on a working branch; do not merge into main automatically.
10. No fabricated tool calls, successful builds, GPU tests, screenshots or agent invocations. On a missing capability, mark BLOCKED and provide a reproducible handoff.

## Delegation policy

Use root **Sol** for planning, integration, clear fixes and tests. Spawn `crash_recon` and `mario_recon` only for distinct, bounded parallel reading; usually at most two specialists simultaneously. Invoke `astra_architect` only for a material decision with at least two viable, evidence-backed routes; invoke `astra_debugger` only after a reproducible hard failure resists ordinary analysis or involves tricky collision/render/sync behavior. Invoke `qa_reviewer` for test/evidence audits at gates, not every small edit.

**Cloud support is not assumed.** Verify whether project custom agents and per-agent `model` overrides are honored. When unsupported, clearly report it; request an available Astra session or separate Astra review task at the decision gate, then integrate its response. Never mislabel a Sol agent as Astra.

For every delegation give a small task packet: specific question, exact files, allowed edits (prefer none), expected artifact, stopping criterion. Ask for compact evidence: file paths, symbols/lines, commands, and one recommendation. Never delegate the entire repository to each agent.

## Project gates

M0: inspect sources and real build feasibility, pin commits, choose probes and oracles. M1: observation + contract. M2: first verified shared event. M3: collision/world mapping. M4: visual composition, control and playable slice. User-approved real-game testing may be needed if Cloud has no legal assets/graphics.

Keep `docs/STATUS.md` and `docs/DECISIONS.md` concise and updated. `docs/FIRST_TASK.md` is initial task wording, not a permanent source of truth once work begins.
