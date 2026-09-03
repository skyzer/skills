---
name: buyer-signal-scanner
description: "Scan public sources (X, Reddit, Hacker News, GitHub, Product Hunt, forums, review sites, job ads) for people showing buying intent for what the operator sells, score the intent 1-10, and draft a public reply and a DM for each strong signal for a human to send. Use this skill whenever the user mentions buyer intent, intent signals, social listening, monitoring mentions, 'who is asking for', 'find people complaining about', scanning Reddit/X/HN for leads, or when a scheduled scan fires. This skill drafts and never sends; cold outbound is the outbound-master skill."
---

# Buyer Signal Scanner

An inbound-flavoured prospecting agent. It finds people who are, right now, in public, asking for or complaining about the thing the operator sells, scores how close they are to buying, and writes the reply a good founder would post, for the operator to post themselves.

It is not the outbound agent. Outbound sends cold email on a schedule to companies that fit a profile. This skill reads what people are already saying and answers the ones worth answering. The two share a business brief and an exclusion list; they share nothing else, and this one never sends.

Everything specific to a product lives in `config/`. Nothing in this skill or its references names a company, market or product, so read the config before doing anything else.

## Before the first run

Check that `config/` exists, or that `CONFIG_DIR` in `.env` points somewhere with a `brief.md` and a `sources.yaml`. If only `config.example/` is present, the operator hasn't configured it. Say so and stop rather than inventing search terms, because an agent guessing at what "buying intent" means for a product it doesn't know produces plausible drafts to the wrong people.

Run `scripts/preflight.py`. It checks the config, the state files and which sources are reachable from this runtime, and tells you which sources need the browser. If it fails, fix the cause rather than skipping it.

## The three rules

**This skill drafts. It never posts, replies, DMs or emails.** There is no send path in the scripts, on purpose. A public reply from a founder's account is the founder's voice; a wrong one is visible to everyone and can't be unsent. The output of a run is a review file with drafts the operator copies into X, Reddit or wherever the signal lives. If you find yourself with a browser open on a reply box, close it. Prefer a missing capability over a written prohibition.

**Unknown, never invented.** A draft may only reference what the signal actually says and what the brief actually claims. If the person's problem isn't clear from the post, the draft asks one clarifying question instead of assuming. If the brief doesn't support a claim, the draft doesn't make it. A signal with a `confidence` below the threshold in `sources.yaml` is saved with `status=needs_review` and gets no draft.

**Recency beats everything.** A buying signal decays in days, not weeks. Anything older than `max_age_days` (default 14) is not a signal, it's history: don't save it, don't draft it. The person has already chosen something. Sort every review file newest first.

## What one run does

1. **Read state.** `state/signals.csv`, `state/seen_signals.csv`, `state/exclusions.csv` and, read-only, `state/prospects.csv` from the outbound skill if they share a state directory. `references/data-model.md` has the schemas.
2. **Search each enabled source** in `config/sources.yaml`. Programmatic sources (Hacker News, GitHub, Reddit when reachable) go through `scripts/search.py`. Sources that block scripts (X, LinkedIn, most forums) are searched with the runtime's own browser or web search using the same query list. See `references/sources.md` for what each source is good for and how to search it.
3. **Qualify and score** every candidate with `references/intent-scoring.md`: 10 is "what should I buy", 5 is "I have the problem this solves", below 5 is rejected. Check the person's recent activity before scoring: a competitor's growth marketer asking "what do you use for X" is a 2, not a 9.
4. **Save** each qualifying signal with `scripts/save_signal.py`. It dedupes against `seen_signals.csv` and against domains already in the outbound pipeline, refuses excluded domains, and drops anything under the score threshold into `needs_review`. Rejected signals go to `seen_signals.csv` with a reason so they don't come back next run.
5. **Draft** a public reply and a DM for every signal at or above the draft threshold, following `references/reply-copy.md`. Write them into the signal row via `scripts/save_signal.py --draft`.
6. **Render** the review file with `scripts/render.py` to `runs/<date>/review.md`: newest first, strongest first within a day, drafts inline, and a "needs a human" section at the top.
7. **Expire.** `scripts/expire.py` moves signals older than `max_age_days` with no operator action to `status=expired`. Run it at the end so the review file never shows a stale signal.

If the operator marks a signal `handed_to_outbound`, `scripts/export_for_outbound.py` writes a CSV the outbound skill's `import_leads.py` reads. That is the only bridge between the two skills, and it runs on request, never automatically.

## The correction loop

When the operator rejects a signal or rewrites a draft, that's the most valuable input the skill gets. Record it:

- A rejected signal: `scripts/save_signal.py --reject <id> --reason "..."`. The reason is appended to `state/rejections.md`, which you read before scoring on every run. Three rejections with the same shape are a rule; write it into `config/sources.yaml` under `reject_if` and say so in the summary.
- A rewritten draft: diff the operator's version against yours, and note what changed in `state/rejections.md` under "voice". Read that section before drafting.

The loop is the product. A scanner that surfaces the same wrong signal twice is worse than no scanner, because the operator stops reading the review file.

## Scoring in one paragraph

Score the person's distance from a purchase, not their fit with the ICP. Fit is a filter (in or out); intent is a number. "Which provider do you use for X, we're switching next month" is a 9 or 10. "X is so painful" is a 5, drafts a helpful reply, no pitch. "Interesting thread about X" is a 2 and is rejected. The full rubric with examples is in `references/intent-scoring.md`; read it before the first scoring pass of a run, not from memory.

## Reference files

Read the one the current step needs rather than all of them up front.

- `references/sources.md`: each source, what it's good for, how to search it, what blocks scripts
- `references/intent-scoring.md`: the 1-10 rubric, the fit filter, the person check, what gets rejected
- `references/reply-copy.md`: the public reply and the DM, the word limits, the never-pitch-on-a-5 rule, banned phrases
- `references/data-model.md`: `signals.csv`, `seen_signals.csv`, statuses, the shared files and what may be read vs written

## Relationship to outbound-master

Same brief, same exclusions, same prospect dedupe, separate everything else. Set `CONFIG_DIR` and `STATE_DIR` in `.env` to the outbound skill's folders to share them. This skill reads `prospects.csv` and never writes it; it writes `signals.csv` and `seen_signals.csv` and the outbound skill never reads them. The bridge is one explicit export. Keeping the two apart is what lets this skill run under a weekly schedule with no send capability while the other runs daily with one.
