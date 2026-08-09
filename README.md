# skills

Agent skills that get a company its first users and its first revenue.

Each skill replaces a specialist a small company can't afford to hire yet, and each is self-contained in its own folder: instructions, scripts, example config, and a real example of its output. They run on Claude Code, Claude Cowork, Codex, or anything else that reads files and runs a shell. State lives in files you own, not in a vendor.

## Install

Point your agent at this repo and name the skill:

> Install the outbound-master skill from github.com/skyzer/skills and set it up.

That's the whole install. The agent clones the repo, runs the skill's `install.sh`, pulls in the dependencies, and walks you through the configuration the skill's own docs describe. Everything an agent needs to know is in each skill's folder; nothing here assumes a human at a terminal.

Doing it by hand instead:

```bash
git clone https://github.com/skyzer/skills
cd skills/outbound-master
./install.sh
pip3 install -r requirements.txt
```

## The skills

| Skill | Function | What it does |
|---|---|---|
| [`outbound-master`](outbound-master/) | Sales | Runs B2B cold outbound end to end: sources, scores, researches a dated hook, writes and deslops the copy, verifies every address, sends idempotently on a spaced schedule, tracks every touch in an append-only event log, and drafts replies a human approves. Refuses to send when it shouldn't. |

More coming. Each new skill lands as its own folder with the same shape.

## For agents

If you're an agent asked to install or run a skill from this repo:

1. Clone the repo and `cd` into the skill's folder.
2. Read the skill's `README.md`, then `skill/SKILL.md`. The SKILL.md is the operating manual; read the reference file for the step you're on rather than all of them up front.
3. Run `./install.sh`, then install `requirements.txt`.
4. Ask the operator for what only they have (credentials, the business brief), and run the skill's preflight before doing anything real.
5. Respect the skill's guards. If a skill ships a dry-run mode, it starts on.

## Design rules every skill here follows

**Configuration is separate from the engine.** Everything about your company lives in `config/`, which is gitignored. Nothing in a skill names a company, market or product.

**State is files, not chat.** Anything needed on the next run exists on disk, because the conversation where you explained it is gone.

**Nothing irreversible happens without a guard.** Sends are idempotent, destructive actions are gated, and anything that spends money, reputation or a relationship stops and asks.

**Skipping is free, being wrong isn't.** Every skill would rather do nothing and say why than do something plausible and wrong.

**Dry run first.** If a skill touches the outside world, it has a mode that shows exactly what it would do and does nothing.

## Licence

MIT.
