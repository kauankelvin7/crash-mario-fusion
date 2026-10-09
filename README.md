# Crash × Mario 64 — Fusion Engineering Lab

**Status (2026-10-09, `m0-recon`):** M2 original-game interaction verified on Windows: collecting a native Mario coin triggered a guarded input pulse and a full native Crash jump/landing trace, corroborated by the user's visual observation. **The games still run in separate windows/worlds**; unified collision, camera, rendering and playable fusion are not implemented.

**Continue development with Codex:** [New PC migration and exact checkpoint](docs/PC_MIGRATION_HANDOFF.md) | [Codex handoff](docs/CODEX_HANDOFF.md) | [Evidence](docs/EVIDENCE.md) | [Windows test instructions](docs/WINDOWS.md). Cloud-safe tests are under `tests/` and `.github/workflows/source-only-checks.yml`; those replay and validate code without commercial game assets. This remains a development probe, **not** a downloadable playable release.

Goal: preserve the actual game simulations of **Crash Bandicoot 1 (1996)** and **Super Mario 64** while studying a verifiable shared-world integration. A cosmetic skin swap is not sufficient.

## Getting started — Codex Cloud

1. Connect this GitHub repository `kauankelvin7/crash-mario-fusion` to Codex Cloud.
2. Continue the existing branch and status; read `docs/WINDOWS.md` for local execution. Select **GPT-6.1 Sol** and Medium reasoning if the model appears in your picker.
3. Make sure the environment can access official/open-source repositories for inspection. Do not upload commercial ROMs or extracted assets.
4. Ask the agent to report whether the **cloud** actually loaded `.codex/agents/*.toml` and whether an Astra subagent can be selected. Do not assume availability from the presence of these files.
5. Run `python -m unittest discover -s tests -v` to check the bootstrap configuration.

**Not automatic:** placing `.codex/agents/*.toml` in Git does not guarantee that Codex Cloud exposes custom agent-model selection. These files follow documented configuration for supported Codex clients. If the cloud does not honor them, start the root job in Sol and use the Astra escalation procedure in `docs/ORCHESTRATION.md` as a separate supported agent/task, without pretending Astra was invoked.

## Model routing

| Role | Model | Trigger |
| --- | --- | --- |
| Root (UI selection) | `gpt-6.1-sol`, medium | Default implementation and coordination |
| Crash investigation | `gpt-6.1-sol`, medium | Read-only, bounded analysis |
| Mario investigation | `gpt-6.1-sol`, medium | Read-only, bounded analysis |
| Architecture review | `gpt-6-astra`, high | Evidence-backed architectural uncertainty |
| Deep fault analysis | `gpt-6-astra`, high | Reproduced hard bugs after bounded normal attempts |
| Verification | `gpt-6.1-sol`, medium | Test sufficiency, evidence, correctness |

## Primary source references

- Universal Modder: https://github.com/rehan-remade/universal-modder
- Mashup skill: https://github.com/rehan-remade/universal-modder/blob/main/skills/mashup-mods/SKILL.md
- Crash recompilation candidate: https://github.com/Matteo842/CrashBandicoot-Launcher
- Crash C port candidate: https://github.com/wurlyfox/c1
- SM64 source: https://github.com/n64decomp/sm64
- SM64 PC host candidate: https://github.com/sm64pc/sm64ex
- Mario movement library candidate: https://github.com/libsm64/libsm64
- Codex subagents: https://developers.openai.com/codex/agent-configuration/subagents

Pin exact upstream commit hashes after inspection. References are candidates, not claims of compatibility or licensing clearance for distribution. Do not copy retail content into Git.
