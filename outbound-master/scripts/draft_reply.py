#!/usr/bin/env python3
"""Draft a reply to an inbound message. Never sends.

Usage:
    python scripts/draft_reply.py --message-id <gmail_id> --body-file draft.txt
    python scripts/draft_reply.py --list

This script has no send path. With Gmail it authenticates using the compose
scope, which cannot send; the guard is the absence of a permission rather than
a rule asking the agent not to use one. A rule in a prompt is a suggestion. A
credential that physically cannot send is a boundary.

The draft lands in the operator's mailbox, in the original thread. They read
it, edit it, and send it themselves, which beats a review queue in a
spreadsheet because the reply goes out with the full history attached.

Providers without drafts (SMTP) write the reply to state/reply_drafts/
instead. Weaker, but the property that matters still holds.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import append_event, config, state_path
from providers import NotSupported, get_mailer


def header(msg, name):
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message-id", help="Gmail id of the message being replied to")
    ap.add_argument("--body-file", help="file containing the reply body")
    ap.add_argument("--body", help="reply body inline (use --body-file for anything long)")
    ap.add_argument("--company", default="", help="company name, for the event log")
    ap.add_argument("--list", action="store_true", help="list drafts waiting for the operator")
    args = ap.parse_args()

    mailer = get_mailer(config())

    if not mailer.supports_drafts:
        # Degrade rather than fail. The important property is unchanged: there
        # is no code path here that sends a reply.
        if not (args.body or args.body_file):
            sys.exit("Need --body or --body-file")
        body = args.body or pathlib.Path(args.body_file).read_text()
        out_dir = state_path("reply_drafts"); out_dir.mkdir(exist_ok=True)
        out = out_dir / f"{(args.company or 'reply').replace('/', '-')}.txt"
        out.write_text(body)
        append_event(args.company or "unknown", "reply_drafted",
                     detail=f"written to {out} (provider has no drafts)")
        print(f"Your email provider has no drafts, so the reply is at {out}.")
        print("Copy it into your mail client, read it, send it yourself.")
        return

    if args.list:
        items = mailer.list_drafts()
        if not items:
            print("No drafts waiting.")
            return
        print(f"{len(items)} draft(s) waiting for you in Gmail:\n")
        svc = mailer._service(mailer.DRAFT_SCOPES)
        for d in items:
            msg = svc.users().messages().get(userId="me", id=d["message"]["id"],
                                             format="metadata").execute()
            print(f"  to {header(msg, 'To'):40s} {header(msg, 'Subject')}")
        print("\nOpen Gmail, read them, send the ones you agree with.")
        return

    if not args.message_id or not (args.body or args.body_file):
        sys.exit("Need --message-id and one of --body / --body-file")

    body = args.body or pathlib.Path(args.body_file).read_text()

    try:
        draft_id, to, subject = mailer.draft_reply(args.message_id, body)
    except NotSupported as exc:
        sys.exit(str(exc))

    append_event(args.company or to, "reply_drafted", person_email=to,
                 detail=f"draft {draft_id}", message_id=args.message_id)

    print("Draft created in the original thread.")
    print(f"  to:      {to}")
    print(f"  subject: {subject}")
    print(f"  draft:   {draft_id}")
    print("")
    print("It is sitting in your drafts. Read it, edit it, send it yourself.")
    print("This script has no send path: the draft credential cannot send.")


if __name__ == "__main__":
    main()
