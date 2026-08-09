# The sequence

Five touches over 28 days. The rule that makes it work: every touch adds something the previous one didn't. No "just bumping this", no "following up on my last email", no resends with a new subject line.

Timings and content come from `config/templates/`. The structure below is why each touch exists.

## Touch 1 — Day 0 — the hook

Their recent news, your one sentence, one question. Under 80 words. See `references/copy-rules.md`.

## Touch 2 — Day 3 — proof

One specific result from a comparable company. Not a case study, one sentence of outcome with a number in it.

If there's no real customer result yet, use a market fact with a source instead. Never invent a customer. A fabricated proof point is the fastest way to lose a deal you were winning, and this industry is small.

Under 60 words. This is where a link is allowed, if there's one worth clicking.

## Touch 3 — Day 10 — pure value, no pitch

Something genuinely useful, with no ask attached. A regulatory change in their market, a data point about their category, a competitor move they'd want to know about.

No CTA. None. The absence is the point: it's the only message in the sequence that costs them nothing to read and asks nothing back, and it's the one that most often gets a reply.

If you can't find something actually useful, skip this touch entirely rather than manufacturing it. A fake value email is worse than silence because it's transparently a pretext.

## Touch 4 — Day 17 — the diagnostic question

One question about how they handle the specific thing your product addresses. Not "are you interested", not "did you see my email". A real question a practitioner would ask a peer.

The question should be answerable in one line, and the answer should be interesting to you regardless of whether it leads anywhere. If you don't care about the answer, it's not a diagnostic, it's a pretext, and it reads like one.

## Touch 5 — Day 28 — the break-up

Honest, no pressure, no guilt. Say the timing looks wrong, describe concretely what day one would look like if it ever became relevant, and close warmly.

Concrete beats vague here. "You'd drop in the widget, we handle the compliance side, your users are transacting within 48 hours" gives them something to remember in six months. "Let me know if anything changes" does not.

No CTA. This is the message that most often gets a reply, usually a variant of "actually, ask me again in Q3", which is worth more than the silence it replaces.

## Stopping rules

Stop the sequence immediately on: any human reply, a bounce, an unsubscribe request in any wording, an out-of-office (pause and resume after the return date), or the prospect appearing in `state/exclusions.csv`.

After touch 5 with no response, the prospect goes back to the pool. Re-score in 90 days when a new signal appears. Don't restart the sequence on the same hook.

## Follow-up coverage

Coverage is the ratio of delivered prospects that received at least one follow-up. It's usually the weakest number in an outbound system, because sending touch one is exciting and sending touch four is admin.

The sequence is where conversations come from. If coverage is under 70%, fixing that is worth more than sourcing new prospects.
