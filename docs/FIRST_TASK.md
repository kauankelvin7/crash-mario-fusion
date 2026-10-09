# Task to paste into Codex Cloud (first milestone only)

You are the principal engineer for Crash × Mario 64 fusion. Read `AGENTS.md`, `docs/ORCHESTRATION.md`, and `docs/STATUS.md` before acting. Use Sol Medium as root if the model is available.

Begin M0 with actual source inspection. Consult the upstream `universal-modder` **mashup-mods** skill and relevant current technique notes. Pin current revisions for the CrashBandicoot-Launcher, c1, sm64, sm64ex and libsm64 candidates only as needed. Don't assume any of them already provide an injectable or headless runtime.

Delegate two bounded read-only investigations (Crash versus Mario) in parallel only if custom agents work; gather file/symbol-based evidence. Verify whether Codex Cloud truly loads project `.codex/agents` and honors model pinning. State that fact explicitly; do **not** claim Astra was run just because `astra_architect.toml` is present.

When an architecture choice requires deep reasoning, invoke `astra_architect` **only if its resolved model is confirmed as GPT-6 Astra**. Otherwise prepare one compact escalation packet per `docs/ORCHESTRATION.md`, set the decision to NEEDS_ASTRA and continue testable nondependent work. Never silently substitute Sol.

Compare dual-process passthrough, embedded runtime/library and hybrid only after reading real entry points. Select the minimum reversible approach with a measurable oracle, and propose a concrete first REAL cross-runtime event. Don't equate a mocked bridge with a playable mashup.

Do not download retail ROMs/assets or commit extracted game files. Inspect Cloud build/GUI access. Run only feasible toolchain tests; report execution limits accurately. Don't benchmark RAM or prematurely optimize. Keep edits minimal: update `docs/STATUS.md`, `docs/DECISIONS.md`, and only add code/tests that can be actually validated in this environment. Avoid creating a generic empty bridge just to show progress.

Quality gates: tests use VERIFIED_REAL, VERIFIED_SYNTHETIC, NOT_TESTED or BLOCKED. Execute the cheapest useful oracle. Max three equivalent attempts; stop and document a blocker rather than looping.

Commit on a working branch. Do not merge or publish main. Finish with (1) inspected pinned revisions, (2) decided or blocked architecture, (3) exact tests/results, (4) whether Astra was actually invoked, (5) files and commits, (6) one next actionable milestone. Don't repeat this prompt in your final reply.
