# Data model

Two files this skill owns, three it borrows, one bridge.

## `state/signals.csv` (owned, fast-decaying)

One row per signal. Unlike the outbound skill's prospects, a signal is a moment, not a company: the same person asking twice a month apart is two rows.

```
id,found_date,source,url,author,author_handle,author_url,company,domain,
posted_date,age_days,text_excerpt,problem,intent_score,confidence,fit,
group,status,reply_draft,dm_draft,operator_note,last_updated
```

- `id`: sha1 of the URL, first 12 chars. Stable across runs, so a re-found signal dedupes.
- `source`: one of the keys in `config/sources.yaml` (`x`, `reddit`, `hn`, `github`, `producthunt`, `forum`, `reviews`, `jobs`, `other`).
- `posted_date` is when the person posted, `found_date` is when the scan found it. `age_days` is computed from `posted_date` at save time and again at render time.
- `text_excerpt`: up to 300 characters of the post, verbatim. Never paraphrased, because the draft is checked against it.
- `problem`: one sentence, the agent's reading of what they are trying to solve. "Unknown" is a valid value and blocks drafting.
- `intent_score`: 1-10 per `intent-scoring.md`. `confidence`: 1-10, how sure the agent is of the score given what it could see.
- `fit`: `yes`, `no`, `unclear`. Only `yes` gets drafts.
- `group`: the brief's group code the author belongs to, if any. Same codes as the outbound brief so an export lands in the right bucket.
- `status`, closed vocabulary:

```
new              saved, drafts written, waiting for the operator
needs_review     saved, below the draft threshold or fit unclear; no drafts
replied          operator posted the public reply (they mark it)
dm_sent          operator sent the DM (they mark it)
handed_to_outbound   exported for the outbound skill's pipeline
rejected         operator or agent rejected; reason in rejections.md
expired          aged past max_age_days with no action
```

`reply_draft` and `dm_draft` hold the current drafts. A rewrite by the operator overwrites them; the agent's original is kept in `runs/<date>/review.md` for the diff.

## `state/seen_signals.csv` (owned, append-only)

```
id,url,seen_date,outcome,reason
```

Every URL the scan has looked at, whether or not it became a signal. `outcome` is `saved`, `rejected`, `duplicate`, `too_old`, `excluded`, `in_outbound_pipeline`. Read before saving; a URL here is skipped without re-scoring. This is what keeps the review file from showing the same post twice, and it's also the record of what the agent decided *not* to surface, which is where the correction loop looks first.

## `state/rejections.md` (owned, prose)

Two sections, both read before scoring and drafting:

```
## Signals
- 2026-09-03 · reddit · <url> · "vendor employee asking for competitor research"
## Voice
- 2026-09-03 · operator cut the second paragraph; keeps replies to one point
```

Three entries with the same shape become a `reject_if` rule in `sources.yaml`.

## Borrowed from the outbound skill (read-only)

- `config/brief.md`: what you sell, to whom, what you may claim. The scanner uses the same file so the two agents never disagree about a claim.
- `state/exclusions.csv`: `domain,company,reason,scope,added_date,added_by`. A signal from an excluded domain is not saved (scope `never`, `competitor`) or saved as `needs_review` with a note (scope `no_cold`: a warm relationship should get a warm reply from the operator, not a draft).
- `state/prospects.csv`: read only for dedupe. If the author's domain is already in the outbound pipeline, the signal is saved with `outcome=in_outbound_pipeline` in `seen_signals.csv` and surfaced in the review file's "already in outbound" section, so the operator can hand the context to that sequence rather than reply cold in public. The scanner never writes to this file.

`STATE_DIR` and `CONFIG_DIR` in `.env` point at those folders. When they are this skill's own folders, the borrowed files can simply be absent, and the scanner behaves as a standalone.

## The bridge: `export_for_outbound.py`

Writes `runs/<date>/handoff.csv` with columns the outbound skill's `import_leads.py` maps by alias: `company,domain,website,group,person,title,x_handle,linkedin,status,date,note`. `status` is `new` and `note` carries the signal URL and excerpt so the hook is already known. Only signals with `status=handed_to_outbound` are exported. The operator runs the import on the other side; nothing crosses automatically.
