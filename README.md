# skills

Agent skills that help a small company ship, win its first users, and reach its first revenue.

Each skill replaces a specialist a small company can't afford to hire yet, and each is self-contained in its own folder: instructions, scripts, example config, and a real example of its output. They run on Claude Code, Claude Cowork, Codex, or anything else that reads files and runs a shell. State lives in files you own, not in a vendor.

## Install

Point your agent at this repo and name the skill:

> Install the outbound-master skill from github.com/skyzer/skills and set it up.

For bounded Pi/DeepSeek coding delegation:

> Install the delegate-wave skill from github.com/skyzer/skills and use it for this repository task.

That's the whole request. The agent fetches the named skill, reads its `SKILL.md`, and performs only the setup that skill declares. Everything an agent needs to know is in each skill's folder; nothing here assumes a human at a terminal.

Doing it by hand instead:

```bash
git clone https://github.com/skyzer/skills
cd skills/outbound-master
./install.sh
pip3 install -r requirements.txt
```

`delegate-wave` requires Python 3, Git, [Pi](https://pi.dev) 0.84.1 or newer, and a DeepSeek API key available through `DEEPSEEK_API_KEY` or Pi's native credential store. It has no Python package dependencies. Install it by linking or copying `delegate-wave/` into `~/.codex/skills/delegate-wave` or the equivalent skills directory for your agent.

## The skills

| Skill | Function | What it does |
|---|---|---|
| [`outbound-master`](outbound-master/) | Sales | Runs B2B cold outbound end to end: sources, scores, researches a dated hook, writes and deslops the copy, verifies every address, sends idempotently on a spaced schedule, tracks every touch in an append-only event log, and drafts replies a human approves. Refuses to send when it shouldn't. |
| [`delegate-wave`](delegate-wave/) | Engineering | Delegates bounded discovery and implementation to Pi with DeepSeek V4, enforces clean-worktree and file-scope gates, records cost and verification, and keeps review and release authority with the controlling agent. |

More coming. Each new skill lands as its own folder with the same shape.

## For agents

If you're an agent asked to install or run a skill from this repo:

1. Clone the repo and `cd` into the requested skill's folder.
2. Find and read its `SKILL.md`. Some legacy skills keep it under `skill/`; standard skills keep it at the skill root.
3. Follow only the installation steps and dependencies that skill declares. Do not invent a generic setup sequence.
4. Ask the operator for what only they have, and run any preflight before doing anything real.
5. Respect the skill's guards. If a skill ships a dry-run mode, it starts on.

## Design rules every skill here follows

**Configuration is separate from the engine.** Everything about your company lives in `config/`, which is gitignored. Nothing in a skill names a company, market or product.

**State is files, not chat.** Anything needed on the next run exists on disk, because the conversation where you explained it is gone.

**Nothing irreversible happens without a guard.** Sends are idempotent, destructive actions are gated, and anything that spends money, reputation or a relationship stops and asks.

**Skipping is free, being wrong isn't.** Every skill would rather do nothing and say why than do something plausible and wrong.

**Dry run first.** If a skill touches the outside world, it has a mode that shows exactly what it would do and does nothing.

## Licence

MIT.
