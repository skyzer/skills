# Scheduler task prompt

This is the whole thing. Paste it into whatever runs your scheduled task (Claude
Cowork scheduled task, cron calling `claude -p`, Codex, a CI job) and change the
two paths.

It is deliberately short. Everything it used to repeat now lives in the skill,
which is the point: a scheduler prompt that restates the rules will drift out of
sync with them, and then you have two sources of truth disagreeing at 3am with
nobody watching.

---

```
You are the outbound agent for <ORG>. You run on a schedule.

Working directory: <ABSOLUTE_PATH_TO_REPO>

Before anything else:
1. Run `python scripts/preflight.py`. If it fails, stop and report why. Do not
   work around it.
2. Read `skill/SKILL.md` and follow it. It holds every rule for sourcing,
   scoring, writing, validating, sending and tracking. Read the reference file
   for the step you are on rather than all of them up front.

Then do one run as SKILL.md describes.

Scope for this run:
- New prospects: up to <N> companies
- Follow-ups: everything due
- Replies: classify and draft, never send

Two rules that hold even if the skill file cannot be read:
- Cold outreach sends without approval. A reply to a human never does. Draft it,
  log it, stop.
- Never send to an address that has not been verified this run.

Finish with a short summary: replies found, follow-ups sent, new sends, bounces,
prospects skipped and why, remaining daily cap, and anything waiting on a human.
Put anything needing a human first.
```

---

## Cadence

Set it in one place, here, not in the skill.

**Daily** is the sensible default. One run, a batch of prospects, follow-ups
that came due, inbox swept. Sequence timings are day-based, so a daily run never
misses one.

**Hourly** makes sense once volume is high enough that a day's work doesn't fit
in one run, or when you want replies noticed within the hour. Nothing breaks:
the daily cap is counted from the event log across all runs, and `send_one.py`
is idempotent, so overlapping runs can't double-send.

**Weekly** works for a small warm list, but you'll miss day-3 follow-ups by
several days and touch 2 loses most of its point.

What matters more than frequency: every run is safe to repeat. If a run dies
halfway, the next one picks up from the checkpoint files and the send log rather
than starting over or re-sending.

## First run on a new install

Leave `DRY_RUN=1` in `.env` and run the schedule for a few days. Read
`runs/<date>/dry-run.md` each time. You are checking three things: the hooks
reference real recent events, the skips have sensible reasons, and the copy
sounds like you rather than like software.

Turn `DRY_RUN` off when the dry runs stop surprising you. Not before.

## Unattended running

The agent runs when nobody is watching, so the failure modes that matter are the
quiet ones.

- **Never blocks on a question.** If something is ambiguous it skips the
  prospect with a reason rather than waiting for an answer nobody will give.
- **Everything needing a human goes at the top of the summary,** because the
  summary is often read hours later on a phone.
- **The daily cap is a hard stop,** counted across runs, so a scheduling mistake
  that fires the task twelve times cannot send twelve batches.
- **Replies never auto-send.** This is the rule most worth protecting when you
  are tempted to speed things up.

## Setting it up in Claude Cowork

Create a scheduled task, paste the prompt above, set the cadence, and point the
working directory at the repo. The task needs access to the folder holding
`.env` and `config/`.

## Setting it up with cron

```bash
# Daily at 09:00
0 9 * * * cd /path/to/outbound-master && claude -p "$(cat scheduler/task-prompt.md)" >> logs/run.log 2>&1
```

Use the fenced block from this file as the prompt, not the whole document.
