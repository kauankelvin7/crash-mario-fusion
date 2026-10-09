# Orchestration and token discipline

## Client capability gate

1. Check selected environment: Codex Cloud, Codex CLI/IDE, or another compatible client.
2. Ask the main agent to list (not imagine) loaded custom agents and the resolved models if the runtime exposes this information.
3. If the environment supports `.codex/agents/*.toml` model pinning: invoke `astra_architect`/`astra_debugger` only at the documented escalation gates.
4. If **Codex Cloud does not provide reliable evidence that the Astra override was used**: keep root Sol work moving, pause the architecture/deep-debug decision, request a separate supported task/session explicitly selecting GPT-6 Astra, save its evidence-backed verdict in `docs/DECISIONS.md` and continue with Sol. Do not fabricate automatic routing. The user may need to perform a model selection manually.

Codex subagent configuration reference: https://developers.openai.com/codex/agent-configuration/subagents

## Delegation matrix

- Parallel read-only recon: `crash_recon`, `mario_recon`, only once per material new revision; two threads maximum.
- Architecture Astra: only when two credible integration routes remain and selection changes implementation effort or gameplay fidelity; parent provides evidence; ask for one decisive test.
- Debug Astra: only for reproducible difficult graphics/collision/timing/ownership issues after at most three materially distinct Sol tests; include previous failures.
- QA reviewer: before advancing each milestone after tests are run.
- Main agent: source editing, implementation, testing, status and commits. Never run write agents against same files simultaneously.

## Escalation task packet

```
Question: [one decision/failure]
Milestone: [M0-M4]
Evidence: [pinned repo revisions; paths/symbols; log/test IDs]
Candidates/expected behavior: [specific alternatives]
Attempts already tried: [<=3, distinct]
Constraints: [real engine fidelity, no commercial assets in Git]
Output: [decision + falsifiable low-cost verification, <=650 words]
Stop: [the decision answered or one blocking missing observation identified]
```

## Cost controls

- Root Sol Medium; do not promote everything to High.
- No speculative all-day parallel agents; no new subagents for dependent one-file steps.
- One source-of-truth `docs/STATUS.md`; one architecture log `docs/DECISIONS.md`.
- Bounded code searches; no transcription of huge upstream files into chat.
- No premature benchmarks, video/rendered art, sound, scripts for showcase or asset generation.
- Call Astra once per distinct escalated question; repeat only with *new decisive evidence*.
