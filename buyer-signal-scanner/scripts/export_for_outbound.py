#!/usr/bin/env python3
"""The one bridge to the outbound skill. Writes runs/<date>/handoff.csv in a
shape outbound-master's import_leads.py maps by column alias, for signals the
operator marked handed_to_outbound. Nothing crosses automatically; you run the
import on the other side:

    python scripts/export_for_outbound.py
    cd ../outbound-master && python scripts/import_leads.py ../buyer-signal-scanner/runs/<date>/handoff.csv --dry-run
"""
import argparse
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import read_signals, run_dir

FIELDS = ["company", "domain", "website", "group", "person", "title", "x_handle",
          "linkedin", "status", "date", "note"]

ap = argparse.ArgumentParser()
ap.add_argument("--include-new", action="store_true",
                help="also export status=new signals with a domain (default: handed_to_outbound only)")
a = ap.parse_args()

rows = read_signals()
want = {"handed_to_outbound"} | ({"new"} if a.include_new else set())
out = run_dir() / "handoff.csv"
n = skipped = 0
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        if r.get("status") not in want:
            continue
        if not (r.get("domain") or r.get("company")):
            skipped += 1
            print(f"skip {r['id']}: no company or domain; outbound needs a company. "
                  f"Find it, set it with --status/--note, or reply in place instead.")
            continue
        handle = r.get("author_handle", "")
        w.writerow({
            "company": r.get("company") or r.get("domain"),
            "domain": r.get("domain", ""),
            "website": f"https://{r['domain']}" if r.get("domain") else "",
            "group": r.get("group", ""),
            "person": r.get("author", ""),
            "title": "",
            "x_handle": handle if r.get("source") == "x" else "",
            "linkedin": r.get("author_url") if "linkedin.com" in (r.get("author_url") or "") else "",
            "status": "new",
            "date": r.get("found_date", ""),
            "note": f"signal {r['intent_score']}/10 on {r['source']} {r['posted_date']}: "
                    f"{r.get('text_excerpt','')[:160]} ({r['url']})",
        })
        n += 1
print(f"wrote {out}: {n} rows, {skipped} skipped for missing company")
