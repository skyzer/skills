# Intent scoring

Two questions, in this order: is this person someone we could sell to (fit, a filter), and how close are they to buying (intent, a number)? Never blend them. A perfect-fit company with no intent is an outbound prospect, not a signal. A high-intent post from someone with no fit is noise.

## The fit filter

From `config/brief.md`: does the author, or the company they speak for, belong to one of the groups? `fit=yes` needs a reason you can write in one line ("runs a remittance app, group REM"). `fit=unclear` when the post shows the problem but not the company; those get saved as `needs_review` for the operator, with no draft. `fit=no` is rejected.

Check the person, not just the post. Open their profile or last few posts. Reject with a reason if they are:

- an employee of a competitor or vendor doing "research"
- a consultant collecting options for a client (fit unclear at best)
- a student, hobbyist, or someone asking on behalf of a hypothetical
- an account that posts the same question across many threads (lead-gen bait)

## The intent scale

| Score | What the post says | What it means | Draft |
|---|---|---|---|
| 10 | "What should I buy / which provider do you use for X? Deciding this week." | Active purchase, decision imminent | reply + DM |
| 9 | "Switching from Y, looking at alternatives." | Active purchase, no deadline stated | reply + DM |
| 8 | "Does anything exist that does X for Z?" | Problem named, searching for a category | reply + DM |
| 7 | "Y just failed / raised prices / dropped our market." | Trigger event, likely to start searching | reply + DM |
| 6 | "How do people handle X?" | Problem named, not yet searching | reply only |
| 5 | "X is painful / broken / a mess." | Same problem, venting | reply only, no pitch |
| 4 | "Anyone else dealing with X?" | Sympathy seeking, no move implied | reject |
| 3 | Sharing an article or opinion about the space | Interest, not intent | reject |
| 2 | Vendor, competitor or job-seeker talking about X | Wrong side of the table | reject |
| 1 | Keyword match, unrelated meaning | Noise | reject |

The draft threshold (default 7 for DM, 5 for public reply) is in `sources.yaml`. Below 5 is rejected and written to `seen_signals.csv` with the score as the reason.

## Modifiers

- **Recency.** Posted today or yesterday: score as read. 3-7 days: minus 1. 8-14 days: minus 2 and flag it. Older than `max_age_days`: not a signal.
- **Replies already there.** If a competitor has already answered and the author thanked them, minus 2. If the thread has 30 vendor replies, the public reply is pointless; draft the DM only and note why.
- **Specificity.** Named budget, volume, corridor, deadline or current vendor: plus 1 (cap 10). Specifics are what make the reply possible without inventing.
- **Job ads** are a special case: a company hiring for the role your product replaces or supports is a 6-7 signal with the company as the author. Draft goes to a named person at the company if one is findable; otherwise `needs_review`.

## Confidence

Separate from the score. 8-10: the post is explicit and the person is identifiable. 5-7: the post is clear but the author is a handle with no company. Below 5: you are inferring most of it. Low confidence with a high score is the dangerous quadrant; it goes to `needs_review` regardless of the score.

## Writing the reasoning

One line each for fit, score and confidence, in the row. "Fit yes: runs a payment app for Nigerian SMEs (REM). Score 8: asks if any provider does CNY payouts from NGN, posted 2 days ago. Confidence 7: handle links to company site." That line is what the operator reads to decide in five seconds, and it's what the correction loop compares against when they disagree.
