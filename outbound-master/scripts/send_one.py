#!/usr/bin/env python3
"""Send exactly one email, idempotently.

Usage:
    python scripts/send_one.py <index> [--run 2026-07-28] [--nosleep]

Reads runs/<run>/6-emails.csv, sends row <index>, appends to runs/<run>/7-sent.jsonl
and to state/events.csv.

The idempotency check is the point of this script. Before sending anything it
reads the send log and skips if this index already went out. That means a crashed
session, a container restart, or an accidental re-run of the whole batch cannot
email someone twice. Everything else here is convenience; that part is a safety
property, and it is what makes it reasonable to give an agent a send button.

With DRY_RUN=1 (the default) it renders and validates everything and sends
nothing.
"""
import argparse
import base64
import csv
import datetime as _dt
import json
import random
import sys
import time
from email.mime.text import MIMEText

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import (DRY_RUN, ROOT, append_event, config, excluded, is_role_address,
                    run_dir, sends_today, state_path)


def load_emails(rd):
    path = rd / "6-emails.csv"
    if not path.exists():
        sys.exit(f"No emails file at {path}. Run the write stage first.")
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def already_sent(rd, index):
    log = rd / "7-sent.jsonl"
    if not log.exists():
        return False
    for line in log.read_text().splitlines():
        try:
            if json.loads(line).get("index") == index:
                return True
        except json.JSONDecodeError:
            continue
    return False


def log_send(rd, record):
    with open(rd / "7-sent.jsonl", "a") as fh:
        fh.write(json.dumps(record) + "\n")


def preflight_row(row, product):
    """Assertions that must hold before an email is allowed out. Each returns a
    reason string on failure, or None."""
    to = (row.get("to") or "").strip()
    if not to:
        return "no recipient"

    ex = excluded(to)
    if ex:
        return f"excluded ({ex.get('scope')}): {ex.get('reason')}"

    verdict_tier = (row.get("verdict_tier") or "").strip()
    if verdict_tier not in ("1", "2"):
        return f"verdict tier {verdict_tier or 'missing'} is not sendable"
    if verdict_tier == "2" and is_role_address(to):
        return "catch-all domain and a role address: needs a named human"

    if (row.get("review_flag") or "").upper() == "TRUE":
        return "hook flagged NEEDS_REVIEW"

    body = row.get("body") or ""
    limit = int((product.get("copy") or {}).get("max_words", 80))
    words = len(body.split())
    if words > limit:
        return f"body is {words} words, limit is {limit}"
    if "—" in body or "—" in (row.get("subject") or ""):
        return "contains an em dash"
    if body.count("http") > int((product.get("copy") or {}).get("max_links_first_touch", 0)) \
            and (row.get("touch") or "1") == "1":
        return "first touch contains a link"

    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("index", type=int)
    ap.add_argument("--run", default=_dt.date.today().isoformat())
    ap.add_argument("--nosleep", action="store_true")
    args = ap.parse_args()

    import os
    rd = run_dir(args.run)
    product = config()
    rows = load_emails(rd)

    if args.index >= len(rows):
        sys.exit(f"Index {args.index} out of range ({len(rows)} emails)")
    row = rows[args.index]

    if already_sent(rd, args.index):
        print(f"SKIP  {args.index} {row.get('company')}: already in the send log")
        return

    cap = int(os.environ.get("DAILY_SEND_CAP", "200"))
    if sends_today() >= cap:
        print(f"STOP  daily cap of {cap} reached")
        sys.exit(3)

    reason = preflight_row(row, product)
    if reason:
        print(f"SKIP  {args.index} {row.get('company')}: {reason}")
        append_event(row.get("company", ""), "skipped", domain=row.get("domain", ""),
                     person_email=row.get("to", ""), detail=reason, run_id=args.run)
        return

    # Spacing survives across invocations because it happens before the send,
    # not after. Each call sleeps its own interval.
    if not args.nosleep and not DRY_RUN:
        lo = float(os.environ.get("SEND_SPACING_MIN_SECONDS", "40"))
        hi = float(os.environ.get("SEND_SPACING_MAX_SECONDS", "65"))
        wait = random.uniform(lo, hi)
        print(f"      spacing {wait:.0f}s")
        time.sleep(wait)

    sender = f"{os.environ.get('SEND_FROM_NAME', '')} <{os.environ.get('SEND_AS', '')}>".strip()

    if DRY_RUN:
        print("=" * 68)
        print(f"DRY RUN  index={args.index}  company={row.get('company')}")
        print(f"From:    {sender}")
        print(f"To:      {row.get('to')}  (tier {row.get('verdict_tier')})")
        print(f"Subject: {row.get('subject')}")
        print(f"Words:   {len((row.get('body') or '').split())}")
        print(f"Checks:  {row.get('checks_passed')}")
        print("-" * 68)
        print(row.get("body"))
        print("=" * 68)
        log_send(rd, {"index": args.index, "company": row.get("company"),
                      "to": row.get("to"), "status": "dry_run",
                      "ts": _dt.datetime.now().isoformat(timespec="seconds")})
        return

    from providers import get_mailer
    message_id, error = get_mailer(product).send(
        to=row["to"], subject=row.get("subject", ""), body=row.get("body") or "",
        from_addr=os.environ.get("SEND_AS", ""),
        from_name=os.environ.get("SEND_FROM_NAME", ""))
    status = "ok" if not error else f"FAIL {error}"

    # Log before anything else. If the process dies here, the send log is still
    # the truth and the next run reconciles from it.
    log_send(rd, {"index": args.index, "company": row.get("company"),
                  "to": row.get("to"), "message_id": message_id, "status": status,
                  "ts": _dt.datetime.now().isoformat(timespec="seconds")})

    action = "follow_up_sent" if str(row.get("touch", "1")) != "1" else "sent"
    append_event(row.get("company", ""), action if status == "ok" else "skipped",
                 domain=row.get("domain", ""), person_email=row.get("to", ""),
                 detail=row.get("subject", "") if status == "ok" else status,
                 run_id=args.run, message_id=message_id or "")

    print(f"{'SENT ' if status == 'ok' else 'FAIL '} {args.index} "
          f"{row.get('company')} -> {row.get('to')} {message_id or status}")


if __name__ == "__main__":
    main()
