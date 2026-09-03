# buyer-signal-scanner

A scanner that finds people asking for what you sell, and drafts the answer.

Outbound goes looking for companies that fit a profile and emails them cold.
This is the other half: people are already, in public, asking "which provider
do you use for X", complaining that their current one dropped their market, or
opening a GitHub issue about the thing your product does. This skill reads
those, scores how close each person is to buying, and writes the reply a good
founder would post, in a review file, for the founder to post.

It never sends. There is no post, reply, DM or email path anywhere in the
scripts, and `preflight.py` fails if one appears. A public reply from your
account is your voice, so it goes out from your hands.

## What one scan does

```
preflight     config, thresholds, which sources this runtime can reach
search        HN, GitHub, Reddit by script; X, forums, reviews, jobs by browser
qualify       is this someone we could sell to (a filter), and who are they really
score         1-10: 10 is "what should I buy", 5 is "this is painful", <5 rejected
save          dedupe, exclusions, already-in-outbound check, recency cut-off
draft         a public reply (help first, disclose, one mention at most) and a DM (7+)
render        runs/<date>/review.md, newest first, humans-needed at the top
expire        anything past 14 days with no action is history, not intent
```

Then you read the review file, post the ones you like, edit the ones you
don't, reject the wrong ones with a reason. The reasons feed the next scan.

## Quickstart

```bash
git clone https://github.com/skyzer/skills
cd skills/buyer-signal-scanner
./install.sh                 # copies config.example/ to config/, creates .env
pip install -r requirements.txt

# fill in config/brief.md and config/sources.yaml
python scripts/preflight.py
python scripts/search.py all --out runs/$(date +%F)/0-candidates.jsonl
```

Then let the agent score and draft (that's judgment, not a script), and:

```bash
python scripts/render.py     # runs/<date>/review.md
```

## Running it next to outbound-master

The two skills share a brief and an exclusion list and nothing else. To share
them, install this skill as a subfolder of your outbound project and point the
paths at the parent:

```
CONFIG_DIR=../config
STATE_DIR=../state
```

Now the scanner reads the same `brief.md` (so it never claims something the
outbound agent wouldn't), the same `exclusions.csv` (so it never drafts to
someone you've asked it not to contact), and `prospects.csv` read-only (so a
signal from a company already in a sequence is flagged rather than answered
cold). It writes `signals.csv`, `seen_signals.csv` and `rejections.md`, which
the outbound skill never reads.

The one bridge is `scripts/export_for_outbound.py`: signals you mark
`handed_to_outbound` become a CSV that `import_leads.py` on the other side
understands. You run both ends; nothing crosses on its own.

## Layout

```
skill/
  SKILL.md                the rules the agent reads every scan
  references/
    sources.md            each source, what it's good for, what blocks scripts
    intent-scoring.md     the fit filter, the 1-10 scale, modifiers, confidence
    reply-copy.md         the public reply, the DM, banned phrases, the five-second test
    data-model.md         signals.csv, seen_signals.csv, statuses, what's borrowed
scripts/
  preflight.py            run first, every time
  search.py               HN (Algolia), GitHub, Reddit; refuses browser-only sources
  save_signal.py          the only writer of signals.csv; all the guards live here
  expire.py               ages out stale signals
  render.py               the review file
  export_for_outbound.py  the bridge, on request
config.example/           copy to config/ and fill in. config/ is gitignored.
scheduler/                the scheduled-task prompt and cadence notes
examples/                 a real review file, redacted
```

## Why it's a separate skill

Different job (listening vs sending), different cadence (weekly vs daily),
different failure mode (a bad public reply is visible to everyone; a bad cold
email is visible to one person who ignores it), and above all a different
capability: this one must not be able to send, and the cleanest way to make
sure of that is to keep it out of the folder that can.
