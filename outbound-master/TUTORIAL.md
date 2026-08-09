# Launch your outbound agent in 15 minutes

Works with Claude Code, Claude Cowork, Codex, or any coding agent that can read files and run shell commands. The skill is instructions plus scripts; your agent is the runtime. Nothing here is specific to one model.

## What you need

- A Google Workspace account you'll send from (or any SMTP server)
- An email verification key from [emaillistverify.com](https://emaillistverify.com) or [millionverifier.com](https://millionverifier.com) — a few dollars, not optional. Unverified sending is how bounce rates hit the high teens and poison your domain.
- Python 3.10+
- A list of companies you want as customers. Even just names — the agent researches the rest.

## Step 1: Install (2 min)

```bash
git clone https://github.com/skyzer/skills
cd skills/outbound-master
./install.sh
pip3 install -r requirements.txt
```

`install.sh` creates `config/` from the examples and a `.env` from the template. Both are gitignored — your business data never enters the repo.

## Step 2: Fill in the brief (5 min, the step that matters)

Open `config/brief.md`. This is not technical configuration — it's the brief you'd hand a new salesperson on day one:

It's a markdown document, not a schema. The fastest way to fill it in is to point your agent at whatever notes you already keep about your offerings and customers and say "build my brief from this", then argue with the draft. The sections:

- **Company** — what you sell, in a customer's words. One credential phrase: the single phrase that kills the first objection your market raises (a licence, a certification, a marquee backer).
- **Offerings** — one subsection per thing you sell, so different cohorts can be pitched different products.
- **Claims** — allowed (what you can evidence) and never (the things that are almost true but aren't). The agent treats the never list as absolute.
- **Sender** — whose name is on the email, and one line of credibility.
- **Cohorts** — who you sell to, in groups, each naming its offering, pain point and angle. This is what stops every email being the same template with the name swapped. Two groups is enough to start.
- **Target markets** — where you actually operate today; deal-shape scoring uses it.

`config/settings.yaml` is the technical half: which mail provider, which verifier, rate limits. Two minutes, then forget it.

## Step 3: Credentials (3 min)

Edit `.env`:

```
GOOGLE_SERVICE_ACCOUNT_FILE=./config/service-account.json
SEND_AS=you@yourdomain.com
SEND_FROM_NAME=Your Name
EMAIL_VERIFIER=emaillistverify
EMAIL_VERIFIER_KEY=your-key
DRY_RUN=1
```

Drop your Google service account JSON into `config/service-account.json` (Workspace admin → domain-wide delegation, `gmail.send` + `gmail.readonly` + `gmail.modify` + `gmail.compose` scopes). Using plain SMTP instead? Set `providers.email.type: smtp` in settings.yaml and the SMTP_* variables in `.env`.

## Step 4: Verify (1 min)

```bash
python3 scripts/preflight.py
```

Green across the board means go. It also scans for credentials in files git would track and refuses if it finds any — run it before your first commit, always.

## Step 5: Import your existing leads (2 min)

You almost certainly have a list already — a spreadsheet, a CRM export, an Apollo or Clay CSV. Point the importer at it:

```bash
python3 scripts/import_leads.py path/to/your_leads.csv --dry-run   # shows how columns map
python3 scripts/import_leads.py path/to/your_leads.csv             # imports
```

Column names don't need to match anything: "Company Name", "Account" and "Organisation" all land in the right place, and unmatched columns are listed rather than silently dropped (`--map "TheirCol=field"` for stragglers). Re-running is safe — imports merge and dedupe. If your export has a status column (Sent, Replied, Bounced...), your history comes across too, so follow-ups pick up where your old system left off instead of starting cold.

No list yet? Skip this — tell your agent to research companies in your cohorts and it starts from zero. Research uses your agent's built-in web search by default; if you'd rather run it through an API (or your runtime has no web tools), set `providers.research.type: brave` or `perplexity` in `config/settings.yaml` and drop `BRAVE_API_KEY` / `PERPLEXITY_API_KEY` into `.env`.

## Step 6: First run

Say to your agent (Claude Code, Codex, whatever you use):

> Read skill/SKILL.md and do one outbound run. DRY_RUN is on.

The agent researches each company for a recent hook, scores them 1–100 against your ICP, writes emails under 80 words, deslops them, validates every address, and then — because DRY_RUN=1 — prints exactly what it *would* send to `runs/<date>/dry-run.md` without sending anything.

Read that file. You're checking three things:

1. Hooks reference real events under 90 days old, not invented ones
2. The skips make sense (thin hooks, catch-all role addresses, excluded domains all refuse)
3. The copy sounds like you, not like software

## Step 7: Go live

Happy with the dry run? Flip `DRY_RUN=0` in `.env` and tell the agent to run again. Sends go out one at a time, 40–65 seconds apart, capped at 200/day, each one logged before the next starts. Re-running a batch can't double-send — the send log is checked before every dispatch.

## Step 8: Schedule it

Paste the prompt block from `scheduler/task-prompt.md` into your scheduler — a Cowork scheduled task, or cron calling your agent's CLI. Daily is the right default. Each run: check the inbox, draft replies (never send them — see below), send due follow-ups, research and send the next batch, log everything.

## The three guards you're trusting

Worth knowing what actually protects you, because none of it is "the AI promised to behave":

1. **Idempotent sends.** One email per script invocation, checked against the log first. Crashes and re-runs can't double-email anyone.
2. **Replies are drafts only.** The reply path authenticates with Gmail's compose scope, which *cannot send*. Drafts land in your mailbox, in-thread; you read and hit send yourself. A bad cold email costs one stranger; a bad reply costs a live deal.
3. **Exclusions enforced in code.** `state/exclusions.csv` — customers, partners, opt-outs, competitors. The send script refuses matches and logs why. Not a prompt rule; a hard stop.

## Day to day

- `python3 scripts/render_tracker.py` — a coloured spreadsheet view of your whole pipeline, generated from the CSVs any time you want to look
- `runs/<date>/summary.md` — what each run did, human items first
- `state/events.csv` — append-only history; your funnel numbers derive from it and can't drift

That's it. The agent handles volume; the files handle judgment.
