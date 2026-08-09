# The brief

This is what you'd hand a new salesperson on their first day: who we are, what
we sell, who we sell to, what we may claim, how we write. The agent reads this
file before every run. Write it in plain prose and tables; it's a document,
not a schema. Replace everything in [brackets].

The fastest way to fill this in: point your agent at whatever notes you
already have about your offerings and customers and say "build my brief from
this". Then argue with the draft.

(Prefer structured data? A `config/brief.yaml` is also supported and overrides
nothing; the agent reads whichever exists. The two numeric copy limits the
send scripts enforce live in `settings.yaml` either way.)

## Company

- Name: [Your Company]
- Website: [https://example.com] · Docs: [https://developers.example.com]
- One-liner, in a customer's words: [what you do, one sentence]
- Category, the noun a prospect would use: [e.g. payments API]
- Credential phrase, the one phrase that kills your market's first objection:
  [e.g. SOC2 certified / licensed in X / backed by Y]
- The offer: [e.g. you'd earn X% on a 2-tier referral]

## Offerings

One subsection per thing you sell. Each cohort below names which offering to
lead with, so a prospect never gets pitched the wrong one.

### [offering-one, e.g. "widget"]

- What it is: [one sentence]
- Pitch emphasis: [what this audience actually cares about]
- Differentiator: [the thing competitors can't say]

### [offering-two, e.g. "api"]

- What it is: [one sentence]
- Pitch emphasis: [...]
- Differentiator: [...]

## Claims

**Allowed** (each one you can evidence):

- [claim you can evidence]

**Never** (almost true but isn't — the agent treats this list as absolute):

- [claim that is close to true but isn't]

Notes: [e.g. feature X is roadmap; say "when it goes live", never as current.]

## Sender

- Name: [Your Name] (first name: [Your])
- Title: [Co-Founder]
- Credibility marker: [e.g. previously co-founded X]
- Email: [you@example.com]

## Cohorts

Who you sell to, in groups. Each cohort gets its own pain point and angle;
that's what stops every email being the same template with the name swapped.
Two cohorts is enough to start.

| Abbr | Cohort | Offering | Pain point | Angle | Signals to watch |
|------|--------|----------|------------|-------|------------------|
| SEG1 | [Consumer platforms whose end users would use what you sell] | [offering-one] | [they want to offer it without building it] | [no engineering time, revenue share] | growth, funding |
| SEG2 | [Companies building products that need your capability underneath] | [offering-two] | [coverage gap in specific markets] | [depth of coverage, compliance handled] | product_launch, expansion, competitor_move |

Fallback angle when a cohort prospect has no recent signal: [an INSIGHT or
PATTERN angle per cohort, or "don't force it" — see copy-rules.]

## Target markets

[List the countries or regions you actually serve today. Deal-shape scoring
uses this; a prospect whose markets you don't cover scores low on overlap.]

## Scoring

The rubric lives in the skill (`references/scoring.md`): product fit 35,
signal strength 30, reachability 20, deal shape 15, missing-data ceiling 50%.
Note here only what you want weighted differently, plus:

- Company size sweet spot: [20–500]
- Re-score after: [90] days
- Warmth bands: 10+ mutuals high (consider an intro first), 4–9 medium, 1–3
  low (note it, don't lead with it), 0 cold.
