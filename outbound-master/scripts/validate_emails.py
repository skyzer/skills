#!/usr/bin/env python3
"""Verify addresses and sort verdicts into three tiers.

Usage:
    python scripts/validate_emails.py --run 2026-07-28
    python scripts/validate_emails.py --email someone@example.com

Reads runs/<run>/4-contacts.csv, writes verdict, verdict_tier and a reason back
to the same file, and caches the result in state/people.csv.

Why three tiers and not two: a catch-all domain accepts every address you throw
at it. That tells you the domain exists, not that the mailbox does. Treating
catch-all as "valid" is how a bounce rate gets into the high teens while the
dashboard says everything verified fine.
"""
import argparse
import csv
import datetime as _dt
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import config, is_role_address, looks_like_person, run_dir, state_path
from providers import get_verifier

_VERIFIER = None


def verify(email):
    global _VERIFIER
    if _VERIFIER is None:
        _VERIFIER = get_verifier(config())
    return _VERIFIER.verify(email)

# Provider verdict -> tier. Tier 1 send, tier 2 conditional, tier 3 never.
VERDICT_TIERS = {
    # emaillistverify
    "ok": 1, "ok_for_all": 2, "unknown": 2, "error": 3,
    "email_disabled": 3, "dead_server": 3, "invalid_mx": 3, "disposable": 3,
    "spamtrap": 3, "attempted_too_long": 3, "smtp_protocol": 2,
    # millionverifier
    "good": 1, "catch_all": 2, "bad": 3, "invalid": 3, "risky": 2,
    # generic
    "valid": 1, "deliverable": 1, "accept_all": 2, "undeliverable": 3,
}


def classify(email, verdict):
    """Return (tier, reason). Tier 2 is only sendable to a named human."""
    tier = VERDICT_TIERS.get(verdict, 3)
    if tier == 3:
        return 3, f"verdict {verdict}: never send"
    if tier == 2:
        if is_role_address(email):
            return 3, ("catch-all domain and a role address: the mailbox may not "
                       "exist. Find a named human.")
        if not looks_like_person(email):
            return 3, "catch-all domain and the local part is not a person's name"
        return 2, f"verdict {verdict}: catch-all, but the local part is a named human"
    return 1, f"verdict {verdict}: clean"


def cache_verdict(email, verdict, tier):
    path = state_path("people.csv")
    if not path.exists():
        return
    rows = list(csv.DictReader(open(path, newline="")))
    if not rows:
        return
    changed = False
    for row in rows:
        if (row.get("email") or "").lower() == email.lower():
            row["email_verdict"] = verdict
            row["verdict_date"] = _dt.date.today().isoformat()
            changed = True
    if changed:
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=_dt.date.today().isoformat())
    ap.add_argument("--email", help="verify a single address and exit")
    args = ap.parse_args()

    if args.email:
        v = verify(args.email)
        tier, reason = classify(args.email, v)
        print(f"{args.email}\n  verdict: {v}\n  tier:    {tier}\n  reason:  {reason}")
        return

    rd = run_dir(args.run)
    path = rd / "4-contacts.csv"
    if not path.exists():
        sys.exit(f"No contacts file at {path}")

    rows = list(csv.DictReader(open(path, newline="")))
    fields = list(rows[0].keys()) if rows else []
    for extra in ("verdict", "verdict_tier", "verdict_reason"):
        if extra not in fields:
            fields.append(extra)

    counts = {1: 0, 2: 0, 3: 0}
    for row in rows:
        email = (row.get("email") or "").strip()
        if not email:
            row.update(verdict="", verdict_tier="3", verdict_reason="no address")
            counts[3] += 1
            continue
        verdict = verify(email)
        tier, reason = classify(email, verdict)
        row.update(verdict=verdict, verdict_tier=str(tier), verdict_reason=reason)
        cache_verdict(email, verdict, tier)
        counts[tier] += 1
        print(f"  tier {tier}  {email:42s} {verdict}")

    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\ntier 1 (send): {counts[1]}   tier 2 (conditional): {counts[2]}   "
          f"tier 3 (never): {counts[3]}")
    if counts[3]:
        print("Tier 3 rows are not dead leads. Most need a named human rather than "
              "a shared mailbox. Put them back in the research queue.")


if __name__ == "__main__":
    main()
