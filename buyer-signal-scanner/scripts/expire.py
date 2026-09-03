#!/usr/bin/env python3
"""Move signals past max_age_days with no operator action to status=expired.
Run at the end of every scan so the review file never shows a stale signal.

    python scripts/expire.py            # apply
    python scripts/expire.py --dry-run  # show what would expire
"""
import argparse
import datetime as _dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import read_signals, write_signals, threshold, age_days

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

max_age = int(threshold("max_age_days", 14))
rows = read_signals()
n = 0
for r in rows:
    age = age_days(r.get("posted_date"))
    r["age_days"] = "" if age is None else age
    if r.get("status") in ("new", "needs_review") and age is not None and age > max_age:
        n += 1
        print(f"expire {r['id']}: {age} days, score {r.get('intent_score')}, {r.get('url')}")
        if not a.dry_run:
            r["status"] = "expired"
            r["last_updated"] = _dt.datetime.now().isoformat(timespec="seconds")
if not a.dry_run:
    write_signals(rows)
print(f"{'would expire' if a.dry_run else 'expired'} {n} of {len(rows)} signals (max {max_age} days)")
