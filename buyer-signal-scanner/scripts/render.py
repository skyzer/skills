#!/usr/bin/env python3
"""Build the review file the operator reads: runs/<date>/review.md.

Newest first, strongest first within a day. Anything needing a human goes at
the top. Drafts are inline so the operator can copy them straight into the
platform; they are never posted by anything in this repo.

    python scripts/render.py
    python scripts/render.py --all     # include replied/expired/rejected history
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import read_signals, run_dir, TODAY, age_days

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true")
ap.add_argument("--out")
a = ap.parse_args()

rows = read_signals()
for r in rows:
    ag = age_days(r.get("posted_date"))
    r["_age"] = 999 if ag is None else ag
    r["_score"] = int(r.get("intent_score") or 0)
rows.sort(key=lambda r: (r["_age"], -r["_score"]))

new = [r for r in rows if r["status"] == "new"]
review = [r for r in rows if r["status"] == "needs_review"]
acted = [r for r in rows if r["status"] in ("replied", "dm_sent", "handed_to_outbound")]
hist = [r for r in rows if r["status"] in ("expired", "rejected")]


def block(r, drafts=True):
    out = [f"### {r['_score']}/10 · {r['source']} · {r['_age']}d · {r.get('author_handle') or r.get('author') or 'unknown'}"
           + (f" · {r['company']}" if r.get("company") else ""),
           f"`{r['id']}` · {r['url']}", "",
           f"> {r.get('text_excerpt','')}", "",
           f"**Problem:** {r.get('problem') or 'Unknown'}  ",
           f"**Why:** {r.get('reasoning','')}  ",
           f"**Confidence:** {r.get('confidence')} · **Fit:** {r.get('fit')}"
           + (f" · **Group:** {r['group']}" if r.get("group") else "")]
    if r.get("operator_note"):
        out.append(f"**Note:** {r['operator_note']}")
    if drafts and r.get("reply_draft"):
        out += ["", "**Public reply (copy, then post it yourself):**", "", "```",
                r["reply_draft"], "```"]
    if drafts and r.get("dm_draft"):
        out += ["", "**DM:**", "", "```", r["dm_draft"], "```"]
    out += ["", f"Mark: `python scripts/save_signal.py --status {r['id']} replied` · "
                f"`--status {r['id']} dm_sent` · `--status {r['id']} handed_to_outbound` · "
                f"`--reject {r['id']} --reason \"...\"`", ""]
    return "\n".join(out)


lines = [f"# Buyer signals · {TODAY.isoformat()}", "",
         f"{len(new)} ready with drafts · {len(review)} need a human decision · "
         f"{len(acted)} acted on · {len(hist)} expired or rejected", "",
         "Nothing in this file has been posted. Every draft is yours to send, edit or bin.", ""]
if review:
    lines += ["## Needs a human first", "",
              "Below the draft threshold, fit unclear, low confidence, a warm relationship, "
              "or already in the outbound pipeline. Decide, then mark or reject.", ""]
    lines += [block(r, drafts=False) for r in review]
lines += ["## Ready: drafts to post", ""]
lines += [block(r) for r in new] or ["Nothing new. Either the sources were quiet or the "
                                    "queries need work; check the scan summary.", ""]
if acted:
    lines += ["## Acted on", ""] + [f"- {r['_score']}/10 · {r['status']} · {r['url']}" for r in acted] + [""]
if a.all and hist:
    lines += ["## History", ""] + [f"- {r['status']} · {r['_score']}/10 · {r['url']}" for r in hist] + [""]

out = pathlib.Path(a.out) if a.out else run_dir() / "review.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines))
print(f"wrote {out}: {len(new)} ready, {len(review)} needs review")
