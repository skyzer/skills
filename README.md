# skills

Agent skills that help a small company build and ship software, win its first users, and reach its first revenue.

## Install

Ask your agent to install a named skill from this repository.

> Install the ci-performance-audit skill from github.com/skyzer/skills and use it to audit our recent CI runs.

For manual installation, copy the named folder into your agent's skills directory, such as `~/.codex/skills/` or `~/.claude/skills/` for a user-wide installation. Keep its `SKILL.md` and references together. Check the skill's prerequisites before running it.

## Engineering skills

| Skill | Use it to |
| --- | --- |
| [`feature-delivery`](feature-delivery/SKILL.md) | Take a feature from brief through a prototype or behavior example, plan, implementation, and review. |
| [`e2e-proof`](e2e-proof/SKILL.md) | Exercise a workflow through its normal entrypoint and record what actually happened. |
| [`ci-performance-audit`](ci-performance-audit/SKILL.md) | Measure CI feedback time and runner-minutes, then rank improvements you can verify against a baseline. |
| [`delegate-wave`](delegate-wave/SKILL.md) | Delegate bounded coding tasks to DeepSeek through Pi while the controller owns design, review, and release. |

Start with feature delivery to agree on behavior and build the change. Use E2E proof when you need evidence from a running candidate. Run the CI audit whenever feedback time or runner cost needs attention. Each skill can also be used on its own.

The CI audit was inspired by [StarSling's CI speedup skill](https://github.com/starslingdev/skills#ci-speedup).

### Delegating coding tasks

| Role | What it does |
| --- | --- |
| **Codex or Claude** | Decomposes the task, makes architecture and product decisions, defines acceptance checks, reviews the diff, and owns commits, PRs, merges, and releases. |
| **DeepSeek V4 Flash** | Handles bounded discovery, mechanical implementation, and test generation through Pi. |
| **DeepSeek V4 Pro** | Handles a difficult, well-specified task after Flash fails once or review finds a reasoning defect. |

`delegate-wave` requires Python 3, Git, [Pi](https://pi.dev) 0.84.1 or newer, and a DeepSeek API key available through `DEEPSEEK_API_KEY` or Pi's native credential store. It has no Python package dependencies.

## Sales skills

[`outbound-master`](outbound-master/) runs B2B cold outbound from lead research and qualification through message drafting, address verification, scheduled sends, and reply drafts for human approval. It records each touch in an append-only event log.

> Install the outbound-master skill from github.com/skyzer/skills and set it up.

For manual setup, follow the [outbound-master setup guide](outbound-master/README.md).

## For agents

If you're an agent asked to install or run a skill from this repo:

1. Clone the repo and `cd` into the requested skill's folder.
2. Find and read its `SKILL.md`. Some legacy skills keep it under `skill/`; standard skills keep it at the skill root.
3. Follow only the installation steps and dependencies that skill declares. Do not invent a generic setup sequence.
4. Ask the operator for what only they have, and run any preflight before doing anything real.
5. Respect the skill's guards. If a skill ships a dry-run mode, it starts on.

## Design rules every skill here follows

**Configuration is separate from the engine.** Everything about your company lives in `config/`, which is gitignored. Skills run against your project’s configuration. Published case studies may name the project they describe.

**State is files, not chat.** Anything needed on the next run exists on disk, because the conversation where you explained it is gone.

**Nothing irreversible happens without a guard.** Sends are idempotent, destructive actions are gated, and anything that spends money, reputation or a relationship stops and asks.

**Skipping is free, being wrong isn't.** Every skill would rather do nothing and say why than do something plausible and wrong.

**Plan before external actions.** Operational skills use their documented dry-run mode when available. The engineering skills can provide a plan before running metered or externally visible checks.

## Licence

MIT.
