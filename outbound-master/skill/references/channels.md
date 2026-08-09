# Channels and verification

## Verification is three tiers, not two

Most tooling gives you "valid" and "invalid" and encourages you to treat the first as safe. It isn't. A catch-all domain accepts every address you throw at it, which tells you the domain exists, not that the mailbox does. That gap is where the bounces that survive validation come from.

So verdicts sort into three tiers:

**Tier 1 — send.** A clean verdict on a specific mailbox (`ok`, `valid`, `deliverable` depending on provider). Send.

**Tier 2 — conditional.** A catch-all or accept-all verdict (`ok_for_all`, `accept_all`, `unknown`). Send **only** if the local part is a named human: `firstname`, `firstname.lastname`, `f.lastname`, `firstnamelastname`. If the local part is a role address, do not send.

**Tier 3 — never.** Invalid, disposable, dead server, bad MX, unknown domain, spam trap. Never send, regardless of how good the prospect is.

Role addresses, for the tier 2 rule:

```
info  support  hello  contact  sales  admin  team  help  office
partnerships  compliance  legal  billing  press  media  careers
noreply  no-reply  enquiries  inquiries  general  mail  desk
```

A tier 2 role address isn't a dead lead. It's a lead that needs a name. Append a `needs_named_contact` event and put it back in the research queue.

`scripts/validate_emails.py` implements this and writes the verdict and tier to `4-contacts.csv`. Verdicts are cached in `state/people.csv` with a date; re-verify anything older than 90 days.

## Finding a named human

In rough order of yield: the company's team or about page, LinkedIn for the role that owns the problem, a recent press release or funding announcement (they quote someone), conference speaker lists, GitHub for technical products, the domain's email pattern applied to a name you found elsewhere and then verified.

Never send to a pattern-guessed address that hasn't come back tier 1. The guess is a hypothesis, verification is the test, and skipping the test is exactly how a bounce rate gets into the high teens.

## When there's no email at all

Whole groups don't publish addresses. A lead with no email is not a dead lead, it's a lead on a different channel. `state/people.csv` carries the alternatives, and the agent uses whichever is populated:

| Channel | When it's right | Notes |
|---|---|---|
| Contact form | Only channel available | Shorter than an email. Expect no reply thread, so include a direct address to reply to. |
| Telegram | Common for crypto, gaming, automation, some marketplaces | Often the fastest reply of any channel. Keep it to two sentences. |
| X / Twitter DM | Founder-led companies, open DMs | Very short. Treat it as an opener to move to email. |
| WhatsApp | Some markets treat it as the business default | Only when the number is published as a business contact. |
| LinkedIn | A named person exists and warmth is available | See `references/relationships.md`. |

Channel choice gets recorded in `4-contacts.csv` and in the event log, so per-channel response rates are countable later.

## Cross-channel rules

One channel per touch. Don't email and DM the same person on the same day: it reads as pressure, not persistence.

Don't restate the email in the DM. If they got both, the second one should add something.

Per-channel caps live in `config/settings.yaml`. Sender reputation is a resource you spend and can't buy back, and that's as true of a Telegram account as it is of a domain.
