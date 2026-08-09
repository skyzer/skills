# Handling what comes back

Reply handling lives in this skill rather than a separate one, because a reply is a state transition in a sequence this skill already owns. Replying well needs to know what was sent, which hook it used, which touch it was, and what the prospect's group is. All of that is here.

## The guard is a missing capability, not a rule

The agent drafts. It cannot send.

`scripts/draft_reply.py` authenticates with Gmail's compose scope, which has no send permission. The draft lands in the operator's Gmail, in the original thread, and they send it themselves.

This matters more than it looks. A rule that says "don't auto-reply" is a sentence in a file that a sufficiently confident model can talk itself past on a run nobody is watching. A credential that physically cannot send is a boundary. When you're deciding where to put a guard, prefer taking away the ability over writing down the prohibition.

The reasoning behind the asymmetry: a bad cold email costs one prospect who probably wasn't going to answer. A bad reply costs a live deal, and you never find out, because people don't tell you why they went quiet. Automate the cheap failure, gate the expensive one.

## Classification

`scripts/check_inbox.py` does a first pass on sender and subject patterns. Read the body yourself before trusting it, because the interesting cases are the ones a regex gets wrong.

| Category | What it looks like | What to do |
|---|---|---|
| **Interested** | Asked a question, wants a call, asked for materials | Draft within the hour. Momentum is most of the value. |
| **Objection** | Raised a concern but didn't close the door | Draft. Acknowledge, answer in one line, soft re-ask. |
| **Not now** | Timing, budget, priorities. No never. | Draft a short acknowledgement. Set a re-score date. |
| **Referral** | Pointed you at a colleague | Draft a thank-you and ask permission to use their name. Add the new person to `people.csv`. |
| **Wrong person** | Not their area, no referral offered | Draft a brief thanks. Research the right person. |
| **Opt-out** | Any wording asking to stop | Add to `state/exclusions.csv` with scope `never`, today, before anything else. No draft. |
| **Out of office** | Auto-reply with a return date | No draft. Pause the sequence, resume after the date. |
| **Auto-reply** | Ticket acknowledgement, no-reply address | No draft. Archive. |
| **Bounce** | Delivery failure | Append `bounced`. If it was a role address on a catch-all domain, flag `needs_named_contact`. |

Anything you can't classify confidently goes to the operator unclassified with the raw text. A wrong guess on an ambiguous reply is worse than admitting you don't know, because the operator can read it in ten seconds.

## Stop the sequence

Any human reply stops the sequence immediately. So does a bounce, an opt-out, or the prospect appearing in exclusions. Out of office pauses rather than stops.

The most damaging thing this system can do is send touch three to someone who replied to touch two. It reads as not listening, and it undoes the work the reply represented. Check for a `reply_received` event before every follow-up, not just at the start of the run.

## Drafting

Same voice as the outbound. Contractions, no em dashes, no AI vocabulary, run the deslop pass. Two differences from cold copy:

**Length follows theirs.** A three-line reply gets a three-line answer. Matching their register matters more here than any word count, because the conversation is now two-sided and length signals effort in both directions.

**Answer the actual question first.** Cold email earns attention by being about them. A reply earns it by being useful immediately. If they asked about pricing, the first sentence is about pricing, not a re-pitch.

Patterns worth following:

- **Interested** — answer, then propose one specific time. Not "when works for you", which makes them do the work.
- **Objection** — acknowledge it as reasonable, one line of substance, one soft question. Never argue, never stack three counterpoints.
- **Competitor objection** — don't run down the competitor. Name one specific dimension where you differ, and leave it.
- **Not now** — accept it cleanly, offer one useful thing with no strings, name a specific month to come back.
- **Referral** — thank them, ask if you can mention their name, keep it to three lines.

## After the draft

Append `reply_drafted` with the draft id. Update the prospect. If the reply changes what you know about them (wrong group, different product fit, a market you didn't know they were in), fix `state/prospects.csv`, because a reply is the most reliable research you'll ever get.

Then tell the operator, at the top of the run summary, with the sender, the gist, and where the draft is. Replies waiting on a human are the only thing in a run that has a clock on it.
