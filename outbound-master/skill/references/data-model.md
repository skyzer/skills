# Data model

Three ideas hold this together: state is split by how often it changes, events are append-only, and status is a closed vocabulary.

## Why the split

Persistent state lives in `state/`. Research about a company is written once and rarely touched. A prospect's status changes constantly. If those share a row, then every status update is a write to the row holding your research, and an agent updating a hundred rows an hour will eventually destroy something it took real work to find.

So: slow-changing data in `prospects.csv` and `people.csv`, fast-changing data in `events.csv`, and the fast-changing file only ever gets appended to.

## `state/prospects.csv`

One row per company. Written when the prospect is found, updated rarely.

```
company,domain,group,product_fit,what_they_do,current_stack,why_we_fit,
country,size_band,website,source,found_date,score,tier,scoring_reasoning,scored_date
```

`product_fit` comes from the brief (`config/brief.md`). `score`, `tier` and `scoring_reasoning` are overwritten on re-score, and `scored_date` records when, so staleness is visible.

## `state/people.csv`

One row per human. A company can have several.

```
company,domain,name,title,role_type,email,email_verdict,verdict_date,
linkedin,x_handle,telegram,other_channel,mutual_connections,mutual_names,
warmth,notes
```

`role_type` is `decision_maker`, `gatekeeper`, `influencer` or `shared_inbox`. A shared inbox is a fallback, never a target when a named person is findable.

`mutual_connections` is an integer. `mutual_names` is optional and free text. See `references/relationships.md` for how warmth is used.

## `state/events.csv`

Append-only. Never edit a row, never delete one. Current status for a prospect is the most recent event for that company.

```
timestamp,company,domain,person_email,channel,action,detail,run_id,message_id
```

`action` is a closed vocabulary:

```
sourced          scored           enriched          skipped
verified         verify_failed    excluded
sent             follow_up_sent   bounced           auto_replied
reply_received   reply_drafted    reply_sent
meeting_booked   closed_won       closed_lost       not_interested
do_not_contact   needs_named_contact
```

If a situation doesn't fit one of these, use the closest and put the nuance in `detail`. Inventing an action breaks every count downstream, and free-text status is how a tracker turns into prose within a week.

**Why append-only matters:** an overwritten status column can only ever tell you where things stand right now. It can't tell you the reply rate, the follow-up coverage, or whether touch three does anything, because the history is gone. Those are the questions worth answering.

## `state/exclusions.csv`

```
domain,company,reason,scope,added_date,added_by
```

`scope`: `never` (no contact of any kind), `no_cold` (relationship exists, warm channels only), `competitor`.

Enforced in `scripts/send_one.py`, which refuses a match and logs it. Not advisory, not a note in a prompt. A rule that lives only in prose is one forgetful run away from an embarrassing email.

## `state/budgets.yaml`

Scarce resources with a remaining count, so a run can spend them deliberately.

```yaml
linkedin_personal_invites:
  limit_per_month: 5
  remaining: 5
  resets: monthly
daily_sends:
  limit: 200
  remaining: 200
  resets: daily
```

Agents allocate a budget well once told it exists, and are completely blind to one that only lives in the operator's head.

## `state/campaign_history.md`

Appended after every batch, read at the start of every run. This is what makes the system compound instead of starting from the same priors forever.

```markdown
## 2026-07-28 — [group]

Sent: N first touch, M follow-ups. Bounced: X. Replies: Y.
Hook types used: SIGNAL n, INSIGHT n, PATTERN n
Best performing subject: "..."
Worked: ...
Didn't: ...
Change next time: ...
```

Questions this eventually answers that nothing else can: does SIGNAL beat INSIGHT in this market, does one product pitch out-reply the other, does the day-10 no-pitch touch earn anything.

## Run checkpoints

`runs/<date>/` holds the per-stage files listed in SKILL.md. They're disposable once the run is reconciled into `state/`, but keep them: they're the audit trail for why a given email said what it said, and they're what you show someone who asks how the system decided.

`7-sent.jsonl` is the exception. It's the authoritative record of what actually left, it's append-only, and `send_one.py` reads it for the idempotency check. Never rewrite it.

## Status derivation

There's no status column anywhere. To get the current state of a prospect, take the most recent event. To get funnel numbers, count first occurrences per company:

- delivered = `sent` events minus companies with a `bounced` event
- responded = companies with any `reply_received`
- follow-up coverage = companies with a `follow_up_sent` ÷ companies delivered

Derived, not stored, so it can't drift out of sync with reality.

## The xlsx

`scripts/render_tracker.py` builds a spreadsheet from state whenever you want to look at one. It's a view, not a source. Edits made in the spreadsheet do not flow back, which is deliberate: one writer, one truth.
