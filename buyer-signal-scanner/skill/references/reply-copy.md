# Reply copy

Two drafts per signal: a public reply where the post lives, and a DM. They are different documents with different jobs.

## The public reply

Its job is to be the most useful answer in the thread, in the operator's voice, so that the author and everyone else reading get something from it whether or not they ever become a customer. It is read by strangers, some of them competitors, all of them allergic to pitches.

Rules:

- **Under 60 words** on X, under 120 on Reddit/HN/forums. Platform limits are in `sources.yaml`.
- **Answer first.** The first sentence addresses their actual question or problem with something specific: a number, a mechanism, a thing to check. No "great question", no restating their post.
- **Mention what you sell at most once, and only at score 7+.** At score 5-6 the reply is pure help; the disclosure is enough ("I work on this at <company>, so biased"). At 7+, one sentence on what you do and an offer to DM detail. Never a link in a public reply unless the platform's norms allow it and the source's `allow_links` is true.
- **Disclose.** Always say you work on a product in this space. An undisclosed vendor reply that gets found out costs more than the lead.
- **Match register.** Reddit lowercase-casual is different from HN terse. Read three top comments in the same thread before drafting.
- **Never invent.** If the brief doesn't state it, the reply doesn't claim it. If their post doesn't say it, the reply asks rather than assumes. "Unknown, never invent" applies to their setup as much as to yours.

## The DM

Its job is to open a one-to-one conversation. It is written only at score 7+ (`dm_threshold` in `sources.yaml`) and only when the platform allows DMs from non-followers or the person has an open contact route.

Rules:

- **Under 80 words.** Same limit as the outbound skill's first touch, for the same reason.
- **Reference the post in the first line**, specifically: "Saw your post about X in r/Y" is the minimum; quoting three words of theirs is better.
- **One concrete thing** you can do for their stated problem, with one number if the brief has one.
- **One question** that moves toward a call or a spec, not "would you be open to a chat".
- **No links in the first DM** unless they asked for one.
- **Sign as the operator**, first name only, with role.

## Banned

The same list as the outbound skill's `copy-rules.md` applies: no "I hope this finds you well", no "quick question", no "I noticed", no "leverage", "seamless", "robust", "cutting-edge", "game-changer", no em dashes, no exclamation marks, no emoji unless the thread is full of them. Add for this skill: no "I saw you were looking for" (they know what they posted), no "we'd love to", no "happy to help" as an opener.

## The five-second test

Read the draft as the author, on a phone, having posted 40 minutes ago and got six replies. Is this the one they answer? If it's the one they screenshot as "vendors in my mentions", delete it and write the pure-help version.

## Voice corrections

`state/rejections.md` has a "Voice" section with every edit the operator has made to a draft. Read it before drafting. When it says "cut the second paragraph" three times, stop writing second paragraphs.
