# outbound-master

An outbound agent that actually sends.

Most agent outbound projects stop at a CSV. This one validates addresses, sends
real email on a spaced schedule, tracks every touch in an append-only log, and
refuses to send when it shouldn't. It runs on Claude Code, Codex, or anything
else that can read files and run a shell, because the state lives in files
rather than in a vendor.

Everything about your product lives in `config/`. Nothing in the skill or the
scripts names a company, market or product, so you can clone this, fill in one
folder, and have your own agent.

## What it does in one run

```
preflight        credentials, config and cap checks, refuses to run if a key is exposed
check inbox      replies, bounces, auto-responders. Replies get drafted, never sent.
queue follow-ups everything due in the 5-touch sequence
research          one recent, dated, specific signal per prospect
write             under 80 words, their news first, one CTA
deslop            a separate pass, with fresh eyes
validate          three verdict tiers, not two
send              one email per invocation, idempotent, spaced
reconcile         append events, write the run summary
```

Each stage writes a numbered file the next one reads, so you can open a
checkpoint mid-run, disagree with it, edit it, and the next stage honours your
edit.

Sourcing new prospects is deliberately not on that list. A run works the
pipeline that exists; finding new companies is a separate ask the operator
triggers ("source prospects", or a specific target), because who enters the
funnel is a decision that shouldn't happen quietly on a schedule.

## Quickstart

```bash
git clone https://github.com/skyzer/skills
cd skills/outbound-master
./install.sh                # copies config.example/ to config/, creates .env
pip install -r requirements.txt

# fill in config/brief.md and config/settings.yaml
# put your credentials in .env

python scripts/preflight.py
```

`DRY_RUN=1` is the default. Everything runs, nothing sends. Leave it on until a
few full runs stop surprising you.

Then paste `scheduler/task-prompt.md` into your scheduler and point it at the
repo.

## Layout

```
skill/
  SKILL.md              the rules the agent reads every run
  references/           read the one the current step needs
    data-model.md       CSV schemas, the closed status vocabulary, events
    scoring.md          the 100-point rubric and the missing-data ceiling
    copy-rules.md       template, banned phrases, the five tests, the deslop pass
    sequence.md         the five touches and what each one is for
    channels.md         verification tiers, and what to do when there is no email
    relationships.md    mutual connections as warmth, scarce-resource budgets
scripts/
  preflight.py          run this first, every time
  validate_emails.py    three-tier verdicts
  send_one.py           one email per invocation, idempotent
  dry_run.py            render everything, send nothing
  check_inbox.py        classify replies, bounces, auto-responders
  render_tracker.py     build a spreadsheet view from state
  import_leads.py      import any CSV/XLSX lead list, merge and dedupe
  research.py          optional web research via Brave Search or Perplexity
config.example/         copy to config/ and fill in. config/ is gitignored.
scheduler/              the scheduled-task prompt and cadence notes
state/                  your data. gitignored.
runs/                   per-run checkpoint files. gitignored.
examples/               a real dry run, so you can see the output before installing
```

## Four design decisions worth knowing about

**Idempotent single-send.** `send_one.py` takes an index, checks the send log,
and skips anything already sent. The session can die, the container can restart,
you can re-run the whole batch by accident, and nobody gets emailed twice.
Everything else here is an optimisation. This one is a safety property, and it's
what makes it reasonable to give an agent a send button at all.

**Events are append-only.** There is no status column anywhere. Current state is
the most recent event for a company, derived rather than stored. An overwritten
status can only tell you where things stand right now; it can't tell you your
reply rate, your follow-up coverage, or whether touch three does anything,
because the history is gone.

**Verification has three tiers, not two.** A catch-all domain accepts every
address you throw at it. That tells you the domain exists, not that the mailbox
does. Tier 2 sends only to a named human, never to `info@`. Conflating catch-all
with valid is how a bounce rate gets into the high teens while the dashboard
says everything verified fine.

**Cold sends autonomously, replies never do.** A bad cold email costs one
prospect who probably wasn't going to answer. A bad reply costs a live deal, and
nobody tells you why they went quiet. Automate the cheap failure, gate the
expensive one.

## Copy

Two rules do most of the work.

**Lead with their news, not with your problem.** An ordering change, not a
content change. A problem statement is an unverifiable claim from a stranger in
the same shape as every other cold email in the inbox. Their recent news goes in
line one, your problem in sentence two, where it's framed by something they
already know is true.

**Deslop is a separate pass.** Write the email, then strip the AI patterns with
fresh eyes. A model asked to write and self-police at the same time produces the
same output and then reports that it avoided everything.

Full rules in `skill/references/copy-rules.md`.

## Safety

- `DRY_RUN=1` by default
- `preflight.py` refuses to run if a credential-shaped string appears in a file
  git would track
- `config/`, `state/`, `runs/`, `.env` and all spreadsheets are gitignored
- exclusions are enforced in `send_one.py`, not remembered in a prompt
- the daily cap is counted from the event log across all runs

If you fork this, run `preflight.py` before your first commit.

## Importing your existing leads

Everyone arriving here already has a list somewhere: a spreadsheet, a CRM
export, an Apollo or Clay CSV. Point the importer at it:

```bash
python scripts/import_leads.py path/to/your_leads.csv --dry-run   # see the mapping
python scripts/import_leads.py path/to/your_leads.csv             # import
```

Columns are matched by name ("Company Name", "Account" and "Organisation" all
land on `company`), anything unmatched is reported rather than silently
dropped, and re-running is safe: imports merge and dedupe instead of
duplicating. If your export has a status column, history is reconstructed,
including the events each status implies (a bounce means a send happened) so
your funnel ratios come out right.

## Where research comes from

By default the agent uses its own web search — Claude Code and Cowork have one
built in, so sourcing and enrichment work with zero extra setup. If your
runtime has no web tools (plain cron), or you want cheaper bulk lookups, set
`providers.research.type` in `config/settings.yaml` to `brave` or `perplexity`
and put the key in `.env`. `scripts/research.py` then handles search, news
with freshness filters, per-domain enrichment, and (with Perplexity) cited
answers to synthesis questions. The rule doesn't change with the provider:
every signal carries a date and a source URL, or it isn't a signal.

## Extending it

The natural extension points are `config/` for a different product or vertical,
and `scripts/` for a channel that isn't email. The skill and references should
stay product-agnostic; if something specific to your business won't fit in
`config/`, that's a signal the abstraction is wrong rather than a reason to
hardcode it.

## Licence

MIT.
