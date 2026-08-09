# Copy rules

Read this in full before writing the first email of a run. Product facts, the credential phrase, the sender identity and the angle per group all come from the brief (`config/brief.md`).

## The shape

```
[Line 1: something that happened to them in the last 90 days]

[Who you are, one clause. What you do, one sentence, connected to the thing in line 1.
 One credential that pre-empts the obvious objection. One number that matters to them.]

[One question.]

[First name]
```

Under 80 words, total. Count them. If it's over, cut rather than compress, because compressed text reads like compressed text.

## Lead with their news, not with your problem

This is an ordering change, not a content change, and it's the single highest-leverage rule here.

The instinct is to open with the problem you solve, because that's what you think about all day. It doesn't work. A problem statement is a claim the reader didn't ask for and can't verify, delivered by a stranger, in the same shape as every other cold email in their inbox. It gets pattern-matched and binned before line two.

The first line has exactly one job and it isn't selling. Its job is to prove a human looked at this specific company before writing. Once that lands, the reader gives you the second sentence, which is where the problem goes, now framed by something they already know is true about themselves.

**How this fails:** "Congrats on the raise!" is not an acknowledgement, it's a merge field. A script could produce it from a database row and every reader can tell. The acknowledgement has to carry a detail that only survives if a person read the actual source: which market, which licence, which corridor, what they said about why. That detail is the whole asset. The warmth around it is optional.

## Hook types

Pick by what the research actually found, not by preference.

| Type | Use when | Shape |
|---|---|---|
| `SIGNAL` | A specific, dated, verifiable event exists | "Saw you [event] last month." |
| `INSIGHT` | No event, but a shift in their market is relevant | "[Shift] is putting [specific pressure] on [their category]." |
| `PATTERN` | Neither, but comparable companies behave predictably | "Companies that [did X] usually hit [Y] about [timeframe] in." |
| `CHALLENGE` | A pain is inferable from their public setup | "How are you handling [specific thing] today?" |

`SIGNAL` is strongest and should be preferred whenever a signal under 90 days old exists. Falling back is fine. Faking a signal is not: an invented or stale "recent" event is worse than no personalization, because it's checkable.

## Confidence and the review gate

Score each hook 1 to 10 before writing the rest of the email.

| Score | Meaning |
|---|---|
| 9-10 | Specific dated event, connected naturally to what you sell |
| 7-8 | Real signal, connection takes one inferential step |
| 6 | Defensible but generic. Sendable. |
| 4-5 | Could apply to most companies in the group |
| 1-3 | Company name in a template |

**Below 6, write `NEEDS_REVIEW` in the hook field, set `review_flag` to TRUE, and don't send.** Flagging is cheaper than polishing a weak angle, and much cheaper than spending a prospect on one.

**The mechanical check that overrides the model's own score:** substitute the company name with `[COMPANY]`. If nothing left in the hook is unique to that company, the confidence is 5 regardless of what was claimed. Models are optimistic about their own copy, and this catches it without argument.

## Hard constraints

- Under 80 words
- Exactly one CTA, and it's a question
- No link in the first email. Links hurt first-touch deliverability. Save them for touch two.
- Plain text. No HTML, no images, no tracking pixels, no signature block with a logo.
- Contractions throughout. "We're", "you'd", "don't".
- No em dashes. Comma, period or parentheses.
- One credential phrase, never a paragraph. Whatever the single objection is in your market, the brief (`config/brief.md`) holds the phrase that answers it.

## Subject lines

Under 60 characters. Lowercase except proper nouns. Include the company name or the specific event.

Good shapes: `[company] + [thing you do]`, `saw [company] just [event]`, `quick question about [company]'s [specific system]`, `re: [specific thing they said or did]`.

Never: "partnership opportunity", "introduction", "exclusive", "quick question" alone, anything with FREE, anything with an exclamation mark.

## Banned phrases

These are spam triggers, AI tells, or both:

```
partnership opportunity      I wanted to reach out        I hope this email finds you well
I'd love to connect          innovative solution          cutting-edge
game-changer                 comprehensive                leverage
unlock                       seamless                     robust
excited to                   circling back                touching base
synergy                      revolutionize                best-in-class
```

Banned openers: "I saw...", "I noticed...", "Congrats on...", "Hope you're well...".

Banned phrase lists are the easy half of this. Negative rules are simple to write and simple for a model to route around while producing the same underlying slop. The five tests below do the real work because they're tests you can fail, not prohibitions you can dodge.

## The five tests

Every email passes all five before it enters `6-emails.csv`.

1. **Swappability.** Replace the company name with a different company in the same group. Does it read identically? Then it's a template. Back it goes.
2. **Temporal.** Does it reference something from the last 90 days? Personalization that isn't recent looks fake, because it is.
3. **Structure variation.** Across a batch of ten, no two emails open with the same sentence structure. Check the batch, not the email.
4. **Rhythm.** Mix short sentences with long ones. Never three consecutive sentences of similar length. Uniform rhythm is the most reliable machine tell there is.
5. **One imperfection.** A parenthetical aside, a self-correction, a colloquialism. Something a person writes and a model tidies away.

Record which tests passed in the `checks_passed` column so a failure is visible in the checkpoint file rather than discovered in a reply.

## The deslop pass

Run this as a separate step after the email is written, with the draft in front of you and no memory of having written it.

Strip:

- AI vocabulary: crucial, robust, comprehensive, leverage, navigate, landscape, realm, foster, holistic, delve, underscore, transformative, pivotal, additionally, enhance, valuable
- Significance inflation: "stands as", "is a testament to", "marks a shift", "pivotal moment"
- Copula avoidance: "serves as" and "functions as" are both "is"
- Negative parallelism: "it's not just about X, it's about Y"
- Rule-of-three padding where the third item is filler
- Filler: "in order to" → "to", "due to the fact that" → "because", "has the ability to" → "can"
- Every em dash
- Uncontracted forms a person would contract

Then add back: varied sentence length, a direct opinion where one belongs, and one rough edge.

Why it's a separate pass: a model asked to write and self-police at the same time does neither well. It produces the same output and then reports that it avoided all the patterns. Two passes, two jobs, and the second one has no ego investment in the first one's work.

## Worked example

Config supplies the product facts; the hook comes from research.

**Before (fails: 200+ words, four value props, problem-first, no recent hook):**

> Hi there, I hope this email finds you well. I wanted to reach out because I believe there may be a great partnership opportunity between our companies. We're a comprehensive, cutting-edge infrastructure provider that enables businesses to seamlessly leverage...

**After (78 words, SIGNAL hook, one CTA, one credential):**

> Saw you picked up the payments licence in [market] last month.
>
> I'm [name], previously [credibility marker], now building [product]. We're a [credential phrase] [category] with [specific coverage], so your [their users] could [outcome] without you building [the thing they'd otherwise build]. You'd earn [the number that matters to them].
>
> Worth a 15-min call?
>
> [First name]

The bracketed credential is the one phrase that answers the objection your market raises before any other. One phrase. Never a paragraph.
