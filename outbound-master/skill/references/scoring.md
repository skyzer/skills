# Scoring

Every prospect gets a number from 1 to 100, a tier, and a sentence explaining how the number was reached. The sentence matters as much as the number, because a score you can't argue with is a score you can't improve.

Weights and bands are configurable in the brief (`config/brief.md`). The defaults below are a starting point, not a law.

## The rubric

**Product fit — 35 points**

| Component | Points | What earns full marks |
|---|---|---|
| Group match | 15 | Falls cleanly into a group in the brief (`config/brief.md`) |
| Would their users actually use it | 12 | Evidence their user base has the need, not just the company |
| Gap in their current stack | 8 | They visibly lack the thing, or run a worse version of it |

**Signal strength — 30 points**

| Component | Points | What earns full marks |
|---|---|---|
| Recency | 12 | Dated event inside 30 days. Scale down to 0 at 90 days. |
| Specificity | 10 | Names a market, product, number or person, not "growth" |
| Signal type weight | 8 | Per the brief (`config/brief.md`) signal weights |

**Reachability — 20 points**

| Component | Points | What earns full marks |
|---|---|---|
| Named decision maker found | 10 | A person and a role, not a shared mailbox |
| Verification verdict | 6 | Clean verdict on a real mailbox |
| Warmth | 4 | Mutual connections, prior contact, shared network |

**Deal shape — 15 points**

| Component | Points | What earns full marks |
|---|---|---|
| Volume potential | 8 | Size suggests the deal is worth the sequence |
| Overlap with what you actually serve | 7 | Their markets are markets you cover today |

## The missing-data ceiling

**If a category has no data behind it, cap that category at 50% of its points.**

Not zero, because absence of evidence isn't evidence of absence. Not a guess, because that's exactly what a model does otherwise: it produces a plausible middling number, and plausible middling numbers are indistinguishable from real ones once they're in a column.

So a prospect with no findable decision maker and no verification result caps at 10 of 20 on reachability, and that shows up in the reasoning as "reachability capped, no named contact found". The cap is what stops an unknown from scoring like an average.

Apply it per category, not to the total.

## Tiers

| Tier | Score | Action |
|---|---|---|
| 1 | 80-100 | Send today |
| 2 | 60-79 | Send this week |
| 3 | 40-59 | Nurture. Re-score when a new signal appears. |
| 4 | 0-39 | Don't work it. Leave it in the list with the reason. |

Tier 4 prospects stay in `state/prospects.csv`. Deleting them means re-finding and re-rejecting them in three months.

## Writing the reasoning

One or two sentences, in `3-scored.csv`, that a person can disagree with. Name the biggest contributor and the biggest drag.

Good: *"Strong group fit and a dated licence announcement 12 days old, but reachability capped at half because the only address is a shared inbox on a catch-all domain."*

Bad: *"Good fit, high priority."*

The test: could someone read this and know what to change to make the score go up? If not, rewrite it.

## Re-scoring

Scores go stale because signals do. Re-score when a new signal appears, when a follow-up cycle completes with no reply, or when the prospect has sat untouched for 90 days. Recency is worth 12 points, so a prospect scored on a 20-day-old signal is a different prospect four months later.
