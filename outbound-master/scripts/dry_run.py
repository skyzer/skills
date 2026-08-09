#!/usr/bin/env python3
"""Render an entire batch without sending anything.

Usage:
    python scripts/dry_run.py [--run 2026-07-28] [--out runs/<run>/dry-run.md]

Runs every pre-send assertion against every row in 6-emails.csv and prints what
would happen, in order, with reasons for anything that would be skipped.

This is the first thing to run on a new install and the thing to run after any
change to the copy rules or the config. It makes every other part of the system
testable, because the alternative to a dry run is discovering the problem in
someone's inbox.
"""
import argparse
import csv
import datetime as _dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import config, run_dir, sends_today
from send_one import preflight_row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=_dt.date.today().isoformat())
    ap.add_argument("--out")
    args = ap.parse_args()

    rd = run_dir(args.run)
    path = rd / "6-emails.csv"
    if not path.exists():
        sys.exit(f"No emails file at {path}. Run the write stage first.")

    product = config()
    rows = list(csv.DictReader(open(path, newline="")))

    lines, would_send, would_skip = [], 0, 0
    lines.append(f"# Dry run — {args.run}\n")
    lines.append(f"{len(rows)} emails staged. {sends_today()} sends already today.\n")

    for i, row in enumerate(rows):
        reason = preflight_row(row, product)
        body = row.get("body") or ""
        if reason:
            would_skip += 1
            lines.append(f"\n## {i}. {row.get('company')} — SKIP\n")
            lines.append(f"**Reason:** {reason}\n")
            lines.append(f"To: `{row.get('to')}` (tier {row.get('verdict_tier')})\n")
            continue

        would_send += 1
        lines.append(f"\n## {i}. {row.get('company')} — would send\n")
        lines.append(f"To: `{row.get('to')}` (tier {row.get('verdict_tier')}) · "
                     f"touch {row.get('touch', '1')} · {len(body.split())} words · "
                     f"hook {row.get('hook_type', '?')} "
                     f"(confidence {row.get('confidence', '?')})\n")
        lines.append(f"**Subject:** {row.get('subject')}\n")
        lines.append("```\n" + body.strip() + "\n```\n")
        if row.get("checks_passed"):
            lines.append(f"Checks: {row.get('checks_passed')}\n")

    lines.append(f"\n---\n\n**Would send {would_send}. Would skip {would_skip}.**\n")
    if would_skip:
        lines.append("\nSkips are not failures. A skipped send costs nothing; a bad "
                     "send costs sender reputation, which you spend and cannot buy back.\n")

    text = "".join(lines)
    out = pathlib.Path(args.out) if args.out else rd / "dry-run.md"
    out.write_text(text)
    print(text)
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
