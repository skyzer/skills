---
name: outbound-master
description: "Run autonomous B2B cold outbound end to end: source and score prospects, research a recent hook for each, write and deslop the copy, validate addresses, send on a spaced schedule, track every touch, and queue follow-ups. Use this skill whenever the user mentions outbound, cold email, outreach, prospecting, lead lists, follow-up sequences, reply handling, or asks to contact companies. Also use it when a scheduled outbound run fires, when someone asks who to contact next, or when they want to draft a first-touch email to a company, even if they don't say the word outbound."
---

# Outbound Master

An outbound agent that actually sends. This skill defines how prospects are scored, how copy is written, when to send, and, more importantly, when not to.

Everything specific to a product lives in `config/`. Nothing in this skill or its references names a company, market or product, so read the config before doing anything else.

## Before the first run

Check that `config/` exists. If only `config.example/` is present, the operator hasn't configured it yet. Say so and stop rather than inventing values, because an agent guessing at an ICP produces plausible output that wastes real sends.

Check `DRY_RUN` in the environment. If it's `1`, everything below runs normally except the actual send. That's the intended state for a new install.

Check that `scripts/` exists. If this skill arrived as a bare `.skill` file, it carries the rules and the references but not the scripts, and that changes what a run can safely do. Without the scripts there is no idempotent send, no exclusion enforcement and no verification, so don't send anything: research, score, and draft, tell the operator what you would have sent and why, and point them at the full repo for the version that runs. Advise-and-draft mode is the useful degradation; improvising a send path is not.

## The two rules that matter most

**Cold outreach sends without approval. Replies to a human never do.**

Reply handling lives in this skill, because a reply is a state transition in a sequence this skill already owns, and replying well needs to know what was sent and why.

The guard is not this sentence. Replies go out through `scripts/draft_reply.py`, which authenticates with Gmail's compose scope and has no send permission at all. It creates a draft in the operator's mailbox, in the original thread, and they send it themselves. Prefer removing the capability over writing down the prohibition: a rule can be talked past on a run nobody is watching, a missing permission cannot.

The asymmetry is about failure cost. A bad cold email costs one prospect who probably wasn't going to answer. A bad reply costs a live deal, and nobody tells you why they went quiet. Automate the cheap failure, gate the expensive one.

See `references/replies.md` for classification and drafting.

**Never send to an address that hasn't been verified this run.**

Not "looks plausible", not "the pattern matches". Verified, with the verdict recorded. A verified address and a deliverable address are still different things, which is why `references/channels.md` splits the verdicts into three tiers rather than two.

## What one run does

Run `scripts/preflight.py` first. It checks config, credentials and the daily cap, and refuses to continue if a credential looks like it's about to be committed. If it fails, fix the cause rather than skipping it.

Then, in order:

1. **Read state.** `state/prospects.csv`, `state/people.csv`, `state/events.csv`, `state/exclusions.csv`, `state/budgets.yaml`. The event log is append-only, so current status for a prospect is the most recent event, not a column you overwrite.
2. **Check the inbox.** `scripts/check_inbox.py` classifies replies, bounces and auto-responders. Archive the noise. For a real reply, append `reply_received`, stop that prospect's sequence, then draft via `scripts/draft_reply.py`. See `references/replies.md`.
3. **Process bounces.** A bounce appends a `bounced` event and, if the address was a role address on a catch-all domain, adds a note that a named human is needed.
4. **Queue follow-ups.** Anything due per `references/sequence.md` that hasn't replied, bounced or been excluded.
5. **Research, write, deslop, validate, send** for prospects already in the pipeline. Pipeline it, don't waterfall it: research a batch of five to ten, write and send that batch, then start the next. Waiting for fifty research results before writing anything wastes the whole run if it dies halfway.
6. **Write the run summary** to `runs/<date>/summary.md` and append to `state/campaign_history.md`. If the queue is running thin, say so in the summary so the operator knows sourcing is due — don't source on your own.

## Sourcing is a separate ask, never part of a run

A run works the pipeline that exists: replies, bounces, follow-ups, sends to prospects already sourced and scored. It does not go looking for new companies. Sourcing happens only when the operator asks for it — "source prospects" (work from the groups in the brief), a specific target ("find 20 freight forwarders in Nigeria"), or a pasted artifact ("any prospects in this list?"). See `references/scoring.md` for scoring what you find.

The reason for the split: sending to an existing pipeline is cheap to verify and bounded by the daily cap, but sourcing decides who enters the funnel at all, and that's a judgment the operator should trigger deliberately rather than have happen quietly on a schedule. An agent that quietly grows its own prospect list is an agent whose mistakes compound while nobody is looking. When the queue runs dry, flag it in the summary; the operator sources when they're ready.

## How research happens

Sourcing and enrichment need web search, and where it comes from is a config decision, not yours: `providers.research.type` in `config/settings.yaml`.

- `agent` (the default): use your own web tools. Cowork and Claude Code both have search built in, and your judgment about which result matters beats any API's ranking.
- `brave`, `perplexity`, or a list of both: call `scripts/research.py` instead — `search` and `news` for signals with freshness filters, `enrich <domain>` for the company picture, `ask` (perplexity only) for synthesis questions. With both configured, each command routes to the provider that's good at it. It returns JSON; weaving it into the checkpoint files is still your job.

Either way the standard is the same: a signal needs a date and a source URL in `2-signals.csv`, and an enrichment claim you can't cite doesn't go in `1-enriched.csv`. If you have neither web tools nor a configured provider, say so and work only from what's already in `state/` — imported leads still get scored on group fit under the missing-data ceiling, they just can't get hooks.

## The checkpoint files

Every stage writes a file the next stage reads, under `runs/<date>/`:

```
0-sourced.csv     company, domain, group, source, found_date
1-enriched.csv    what they do, current stack, founder, socials, why we fit
2-signals.csv     one row per signal: type, date, url, freshness_days
3-scored.csv      score, tier, sub-scores, scoring_reasoning
4-contacts.csv    email, verdict, named_person, title, channel, source
5-hooks.csv       hook_text, hook_type, confidence, review_flag
6-emails.csv      subject, body, word_count, checks_passed
7-sent.jsonl      append-only send log
```

Write each one before starting the next stage. The point isn't tidiness: it's that the operator can open `3-scored.csv` mid-run, disagree with a score, edit it, and the next stage honours the edit. It also means a crashed run resumes from the last completed file instead of starting over.

Schemas are in `references/data-model.md`.

## Sending

Never send in a loop from inside the agent. Call `scripts/send_one.py <index>` once per email. That script checks the send log and skips anything already sent, so a crashed session, a container restart, or an accidental re-run can't email someone twice. That idempotency is the property that makes it safe to give an agent a send button at all.

After each send, append the event before starting the next one. If the run dies between the send and the write, the send log is still the truth and the next run reconciles from it.

Respect `DAILY_SEND_CAP` across the whole day, not per run. Count from the event log.

## Exclusions

`scripts/send_one.py` refuses any address matching `state/exclusions.csv` and logs the reason. Don't work around it. If a prospect should come off the list, that's an operator decision and it happens by editing the file.

Scopes: `never` (no contact of any kind), `no_cold` (existing relationship, warm channels only), `competitor`.

## Reference files

Read the one the current step needs rather than all of them up front.

- `references/data-model.md`: CSV schemas, the closed status vocabulary, how events work
- `references/scoring.md`: the 100-point rubric, tiers, the missing-data ceiling
- `references/copy-rules.md`: the template, the word limit, banned phrases, the five tests, the deslop pass
- `references/sequence.md`: the five touches and what each one is for
- `references/channels.md`: verification verdict tiers, and what to do when there's no email
- `references/relationships.md`: mutual connections as a warmth score, scarce-resource budgets
- `references/replies.md`: classifying what comes back, drafting, and why the guard is a missing scope

## Writing copy

Read `references/copy-rules.md` in full before writing the first email of a run. Two things from it that get skipped most often:

**Lead with their news, not with your problem.** The first line's only job is to prove a person looked at this company. A problem statement is an unverifiable claim from a stranger and it's the shape of every other cold email in the inbox. Their recent news goes in line one, your problem goes in sentence two, where it's framed by something they already know is true.

**Deslop is a second pass, not an instruction.** Write the email, then run it through the deslop rules as a separate step with fresh eyes. A model asked to write and self-police simultaneously produces the same output and then congratulates itself for avoiding it.

## When not to send

Skip the prospect and record why. A skipped send costs nothing; a bad send costs sender reputation, which you spend and can't buy back.

Skip when: the hook confidence is below 6 (write `NEEDS_REVIEW` in `5-hooks.csv`), the address verdict isn't sendable, the domain is excluded, the daily cap is reached, no signal newer than 90 days exists and no fallback angle in the brief (`config/brief.md`) fits, or the prospect has replied and is awaiting an operator decision.

## Summary at the end of every run

Short and factual: replies found, follow-ups sent, new sends, bounces, prospects skipped and why, remaining daily cap, and anything waiting on the operator. If something needs a human, put it first.
