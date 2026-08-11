#!/usr/bin/env python3
"""Classify what came back: replies, bounces, auto-responders.

Usage:
    python scripts/check_inbox.py [--since 2026-07-20] [--archive]

Prints a JSON summary and appends events. It does NOT draft or send replies:
that stays with the agent, and sending a reply stays with a human.

Why the split: a bad cold email costs one prospect who probably wasn't going to
answer. A bad reply costs a live deal, and nobody tells you why they went quiet.
Automate the cheap failure, gate the expensive one.
"""
import argparse
import base64
import datetime as _dt
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import append_event, read_events

BOUNCE_SENDERS = re.compile(
    r"(mailer-daemon|postmaster|mail delivery|delivery status|no-?reply)", re.I)
BOUNCE_SUBJECTS = re.compile(
    r"(undeliverable|delivery (has )?failed|returned mail|delivery status "
    r"notification|address not found|mail delivery subsystem)", re.I)
AUTO_SUBJECTS = re.compile(
    r"(out of (the )?office|auto(matic)?[- ]?reply|automatic response|on (annual )?"
    r"leave|vacation|away from|maternity|paternity)", re.I)
UNSUB = re.compile(
    r"(unsubscribe|remove me|take me off|stop (emailing|contacting)|do not contact|"
    r"opt.?out)", re.I)
SMTP_CODE = re.compile(
    r"Diagnostic-Code:\s*smtp;\s*([45]\d\d[^\r\n]{0,60})"
    r"|\b([45]\d\d[ -]\d\.\d{1,3}\.\d{1,3})\b", re.I)


def service():
    from providers import get_mailer
    from common import config
    return get_mailer(config()).read_service()


def header(msg, name):
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def body_text(msg):
    def walk(part):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode(errors="ignore")
        for sub in part.get("parts", []) or []:
            found = walk(sub)
            if found:
                return found
        return ""
    return walk(msg.get("payload", {}))[:4000]


def known_companies():
    """Map a domain back to the company we contacted, so a reply can be attributed."""
    mapping = {}
    for e in read_events():
        if e.get("person_email") and e.get("company"):
            mapping[e["person_email"].split("@")[-1].lower()] = e["company"]
    return mapping


def classify(sender, subject, text):
    if BOUNCE_SENDERS.search(sender) or BOUNCE_SUBJECTS.search(subject):
        return "bounced"
    if AUTO_SUBJECTS.search(subject):
        return "auto_replied"
    if UNSUB.search(text) or UNSUB.search(subject):
        return "do_not_contact"
    return "reply_received"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=(_dt.date.today() - _dt.timedelta(days=7)).isoformat())
    ap.add_argument("--archive", action="store_true",
                    help="archive bounces and auto-responders (never touches real replies)")
    args = ap.parse_args()

    svc = service()
    query = f"in:inbox after:{args.since.replace('-', '/')}"
    listing = svc.users().messages().list(userId="me", q=query, maxResults=200).execute()

    companies = known_companies()
    summary = {"reply_received": [], "bounced": [], "auto_replied": [],
               "do_not_contact": [], "ignored": 0}

    for stub in listing.get("messages", []):
        msg = svc.users().messages().get(userId="me", id=stub["id"], format="full").execute()
        sender = header(msg, "From")
        subject = header(msg, "Subject")
        text = body_text(msg)
        domain = re.search(r"@([\w.-]+)", sender)
        domain = domain.group(1).lower() if domain else ""
        company = companies.get(domain)

        if not company:
            summary["ignored"] += 1
            continue

        action = classify(sender, subject, text)
        if action == "bounced":
            # The SMTP code (550 5.1.1 = dead address, 4.x.x = retryable,
            # 5.7.x = blocked/reputation) lives in the DSN body, not the
            # subject. Fixed prefix so `detail` stays splittable on " | ".
            m = SMTP_CODE.search(text)
            code = (m.group(1) or m.group(2)).strip() if m else "code-not-found"
            detail = f"{code} | {subject}"
        elif action == "reply_received":
            detail = text.strip().split("\n")[0][:200]
        else:
            detail = subject
        append_event(company, action, domain=domain, person_email=sender,
                     detail=detail, message_id=stub["id"])
        summary[action].append({"company": company, "from": sender,
                                "subject": subject, "id": stub["id"],
                                "snippet": text.strip()[:400]})

        if args.archive and action in ("bounced", "auto_replied"):
            svc.users().messages().modify(userId="me", id=stub["id"],
                                          body={"removeLabelIds": ["INBOX"]}).execute()

    print(json.dumps({k: (v if isinstance(v, int) else len(v)) for k, v in summary.items()},
                     indent=2))
    if summary["reply_received"]:
        print("\nHUMAN REPLIES — draft a response, do not send it:\n")
        for r in summary["reply_received"]:
            print(f"  {r['company']}: {r['subject']}\n    {r['snippet'][:200]}\n")
    if summary["do_not_contact"]:
        print("\nOPT-OUTS — add these domains to state/exclusions.csv now:\n")
        for r in summary["do_not_contact"]:
            print(f"  {r['company']} ({r['from']})")

    out = pathlib.Path("runs") / _dt.date.today().isoformat() / "inbox.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
