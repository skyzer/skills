#!/usr/bin/env python3
"""Import an existing lead list into state/. Any CSV or XLSX, any column names.

Usage:
    python scripts/import_leads.py path/to/leads.csv --dry-run     # see the mapping first
    python scripts/import_leads.py path/to/leads.csv
    python scripts/import_leads.py path/to/tracker.xlsx --sheet "My Leads"
    python scripts/import_leads.py path/to/leads.csv --map "Firm=company,Site=website"

Everyone arriving here already has a lead list somewhere: a spreadsheet, a CRM
export, an Apollo/Clay/HubSpot CSV. This script takes whatever that export
looks like and folds it into the three state files:

    prospects.csv   one row per company
    people.csv      one row per human (if your export has contact columns)
    events.csv      appended history (if your export has a status column)

Columns are matched by name against common aliases, case-insensitively, so
"Company Name", "Account", and "Organisation" all land on `company`. Anything
unmatched is reported, not silently dropped. Use --map for the stragglers.

Imports MERGE: re-running the same file, or importing a second list, dedupes by
company + domain instead of erroring or duplicating. Safe to run repeatedly.

If your export has a status column (Sent, Replied, Bounced...), one event per
row is reconstructed, plus the events that state necessarily implies: a bounce
means a send happened, a reply means a send happened. Without that backfill
every funnel ratio comes out wrong, because the denominators are missing.
"""
import argparse
import csv
import datetime as _dt
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import EVENT_FIELDS, STATE_DIR

# ---------------------------------------------------------------------------
# Column aliases. Matched case-insensitively after stripping spaces/_/-.
# ---------------------------------------------------------------------------
ALIASES = {
    "company":   ["company", "companyname", "account", "accountname", "organisation",
                  "organization", "org", "firm", "business", "name"],
    "domain":    ["domain", "companydomain", "domainname"],
    "website":   ["website", "url", "site", "web", "homepage", "companywebsite"],
    "cohort":    ["cohort", "category", "segment", "vertical", "industry", "type"],
    "what_they_do": ["whattheydo", "description", "about", "summary"],
    "current_stack": ["currentstack", "currentpayment", "currentpaymentcrypto",
                      "techstack", "stack", "currentprovider", "currentcryptoprovider"],
    "why_we_fit": ["whywefit", "whytheyneedus", "fit", "whyfit",
                   "whywidgetfits"],
    "country":   ["country", "location", "region", "hq", "headquarters"],
    "person":    ["person", "contactname", "founder", "founderceo", "ceo",
                  "keyperson", "founderkeyperson", "contact", "founderskey people",
                  "founderskeypeople", "fullname", "firstname"],
    "title":     ["title", "role", "titlerole", "position", "jobtitle"],
    "email":     ["email", "emailaddress", "contactemail", "workemail", "contactused",
                  "contactinfo"],
    "linkedin":  ["linkedin", "linkedinurl", "linkedinprofile"],
    "x_handle":  ["x", "xtwitter", "twitter", "twitterhandle", "xhandle"],
    "telegram":  ["telegram", "tg"],
    "mutual_connections": ["mutualconnections", "mutuals", "sharedconnections"],
    "status":    ["status", "stage", "outreachstatus", "state", "dealstage"],
    "date":      ["date", "lastactiondate", "lastcontact",
                  "lastcontactdate", "lasttouch", "updated"],
    "priority":  ["priority", "tier", "score", "rank"],
    "detail":    ["responsenotes", "nextstep", "note", "comments", "remarks"],
}

STATUS_TO_ACTION = {
    "sent": "sent", "emailed": "sent", "contacted": "sent", "first touch": "sent",
    "follow-up sent": "follow_up_sent", "followup sent": "follow_up_sent",
    "followed up": "follow_up_sent",
    "bounced": "bounced", "bounce": "bounced",
    "invalid email": "verify_failed", "invalid": "verify_failed",
    "in conversation": "reply_received", "replied": "reply_received",
    "reply": "reply_received", "responded": "reply_received",
    "engaged": "reply_received", "inbound - awaiting reply": "reply_received",
    "interested": "reply_received",
    "meeting booked": "meeting_booked", "meeting": "meeting_booked",
    "demo booked": "meeting_booked", "call booked": "meeting_booked",
    "won": "closed_won", "closed won": "closed_won", "customer": "closed_won",
    "lost": "closed_lost", "closed lost": "closed_lost",
    "not interested": "not_interested", "declined": "not_interested",
    "rejected": "not_interested",
    "do not contact": "do_not_contact", "dnc": "do_not_contact",
    "unsubscribed": "do_not_contact",
    "auto-responded": "auto_replied", "ooo": "auto_replied",
    "ready to send": "scored", "qualified": "scored",
    "research": "sourced", "new": "sourced", "lead": "sourced",
    "needs named contact": "needs_named_contact",
}

# An end state implies the events that must have preceded it. Without this,
# a "Bounced" row has no matching send and every ratio's denominator is wrong.
IMPLIED_BY = {
    "bounced": ["sent"],
    "follow_up_sent": ["sent"],
    "reply_received": ["sent"],
    "auto_replied": ["sent"],
    "not_interested": ["sent", "reply_received"],
    "meeting_booked": ["sent", "reply_received"],
    "closed_won": ["sent", "reply_received"],
    "closed_lost": ["sent", "reply_received"],
}

PROSPECT_FIELDS = ["company", "domain", "cohort", "product_fit", "what_they_do",
                   "current_stack", "why_we_fit", "country", "size_band", "website",
                   "source", "found_date", "score", "tier", "scoring_reasoning",
                   "scored_date"]
PEOPLE_FIELDS = ["company", "domain", "name", "title", "role_type", "email",
                 "email_verdict", "verdict_date", "linkedin", "x_handle", "telegram",
                 "other_channel", "mutual_connections", "mutual_names", "warmth", "notes"]

ROLE_LOCALS = {"info", "support", "hello", "contact", "sales", "admin", "team",
               "help", "office", "partnerships", "compliance", "desk"}


def squash(name):
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def build_mapping(headers, overrides):
    """Map each source header to a canonical field, or None."""
    mapping, used = {}, set()
    for header in headers:
        if header in overrides:
            mapping[header] = overrides[header]
            used.add(overrides[header])
            continue
        key = squash(header)
        hit = None
        for field, aliases in ALIASES.items():
            if field in used and field != "detail":
                continue  # first match wins per field, except free-text notes
            if key in [squash(a) for a in aliases]:
                hit = field
                break
        mapping[header] = hit
        if hit:
            used.add(hit)
    return mapping


def read_rows(path, sheet=None):
    path = pathlib.Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xltx"):
        try:
            import openpyxl
        except ImportError:
            sys.exit("Reading .xlsx needs openpyxl: pip install -r requirements.txt")
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
        data = [r for r in ws.values]
        if not data:
            return [], []
        headers = [str(h).strip() if h else f"col{i}" for i, h in enumerate(data[0])]
        return headers, [dict(zip(headers, r)) for r in data[1:] if r and any(r)]
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def domain_of(email, website=""):
    if email and "@" in str(email):
        return str(email).split("@")[-1].strip().lower()
    if website:
        return re.sub(r"^https?://(www\.)?", "", str(website)).split("/")[0].strip().lower()
    return ""


def load_existing(path, key_fields):
    if not path.exists():
        return {}, []
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    index = {tuple(squash(r.get(k)) for k in key_fields): r for r in rows}
    return index, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="CSV or XLSX export from your current lead system")
    ap.add_argument("--sheet", help="sheet name, for xlsx with several tabs")
    ap.add_argument("--map", default="", help='overrides: "TheirCol=company,Other=email"')
    ap.add_argument("--source", default="", help="label for where these leads came from")
    ap.add_argument("--dry-run", action="store_true", help="show the mapping and counts, write nothing")
    args = ap.parse_args()

    overrides = {}
    for pair in filter(None, args.map.split(",")):
        src, _, dst = pair.partition("=")
        if dst not in ALIASES and dst not in ("person",):
            sys.exit(f"--map target {dst!r} is not a known field. "
                     f"Known: {', '.join(ALIASES)}")
        overrides[src.strip()] = dst.strip()

    headers, rows = read_rows(args.file, args.sheet)
    if not rows:
        sys.exit(f"No data rows found in {args.file}")

    mapping = build_mapping(headers, overrides)
    print(f"{len(rows)} rows in {pathlib.Path(args.file).name}\n")
    print("Column mapping:")
    unmatched = []
    for header, field in mapping.items():
        marker = field or "(not imported)"
        print(f"  {str(header)[:32]:34s} -> {marker}")
        if not field:
            unmatched.append(header)
    if unmatched:
        print(f"\nUnmatched columns are skipped, not lost — your source file is "
              f"untouched. To import one, add --map \"{unmatched[0]}=<field>\".")
    if "company" not in mapping.values():
        sys.exit("\nNo company column found. That one is required. "
                 "Point at it with --map \"YourColumn=company\".")

    src_label = args.source or f"import:{pathlib.Path(args.file).stem}"
    today = _dt.date.today().isoformat()

    def get(row, field):
        for header, mapped in mapping.items():
            if mapped == field and row.get(header) not in (None, ""):
                return str(row[header]).strip()
        return ""

    prospects, people, events = [], [], []
    for row in rows:
        company = get(row, "company")
        if not company:
            continue
        email = get(row, "email")
        # a cell with several emails/lines: take the first address-looking token
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", email)
        email = email_match.group(0) if email_match else ""
        domain = get(row, "domain") or domain_of(email, get(row, "website"))

        prospects.append({
            "company": company, "domain": domain, "cohort": get(row, "cohort"),
            "product_fit": "", "what_they_do": get(row, "what_they_do"),
            "current_stack": get(row, "current_stack"),
            "why_we_fit": get(row, "why_we_fit"), "country": get(row, "country"),
            "size_band": "", "website": get(row, "website"), "source": src_label,
            "found_date": today, "score": "", "tier": "",
            "scoring_reasoning": "imported, not yet scored", "scored_date": "",
        })

        person = get(row, "person")
        if person or email or get(row, "linkedin"):
            local = email.split("@")[0].lower() if email else ""
            people.append({
                "company": company, "domain": domain,
                "name": person.split("\n")[0], "title": get(row, "title"),
                "role_type": "shared_inbox" if local in ROLE_LOCALS
                             else ("decision_maker" if person else ""),
                "email": email, "email_verdict": "", "verdict_date": "",
                "linkedin": get(row, "linkedin"), "x_handle": get(row, "x_handle"),
                "telegram": get(row, "telegram"), "other_channel": "",
                "mutual_connections": re.sub(r"\D", "", get(row, "mutual_connections")) or "0",
                "mutual_names": "", "warmth": "", "notes": get(row, "detail"),
            })

        status = get(row, "status").lower()
        action = STATUS_TO_ACTION.get(status)
        if action:
            raw_date = get(row, "date")
            ts = f"{raw_date[:10]}T12:00:00" if re.match(r"\d{4}-\d{2}-\d{2}", raw_date) \
                 else f"{today}T12:00:00"
            base = _dt.datetime.fromisoformat(ts)
            for offset, prior in enumerate(reversed(IMPLIED_BY.get(action, [])), 1):
                events.append(dict(zip(EVENT_FIELDS, [
                    (base - _dt.timedelta(seconds=offset)).isoformat(timespec="seconds"),
                    company, domain, email, "email", prior,
                    f"inferred on import: '{status}' implies this happened",
                    src_label, ""])))
            events.append(dict(zip(EVENT_FIELDS, [
                ts, company, domain, email, "email", action,
                f"imported from status '{status}': {get(row, 'detail')[:120]}",
                src_label, ""])))

    # ---- merge into state ----
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p_path, pe_path, ev_path = (STATE_DIR / n for n in
                                ("prospects.csv", "people.csv", "events.csv"))

    p_index, p_rows = load_existing(p_path, ["company", "domain"])
    added_p = 0
    for p in prospects:
        key = (squash(p["company"]), squash(p["domain"]))
        if key in p_index:
            existing = p_index[key]
            for field in PROSPECT_FIELDS:   # fill blanks, never overwrite
                if not existing.get(field) and p.get(field):
                    existing[field] = p[field]
        else:
            p_index[key] = p
            p_rows.append(p)
            added_p += 1

    pe_index, pe_rows = load_existing(pe_path, ["company", "email", "linkedin"])
    added_pe = 0
    for p in people:
        key = (squash(p["company"]), squash(p["email"]), squash(p["linkedin"]))
        if key not in pe_index:
            pe_index[key] = p
            pe_rows.append(p)
            added_pe += 1

    existing_ev = set()
    if ev_path.exists():
        with open(ev_path, newline="") as fh:
            existing_ev = {(squash(e["company"]), e["action"], e["timestamp"][:10])
                           for e in csv.DictReader(fh)}
    new_events = [e for e in events
                  if (squash(e["company"]), e["action"], e["timestamp"][:10]) not in existing_ev]

    print(f"\nWould add: {added_p} prospects ({len(prospects) - added_p} already known, "
          f"blanks filled), {added_pe} people, {len(new_events)} events")

    if args.dry_run:
        print("--dry-run: nothing written")
        return

    for path, rws, fields in ((p_path, p_rows, PROSPECT_FIELDS),
                              (pe_path, pe_rows, PEOPLE_FIELDS)):
        with open(path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rws)
    is_new = not ev_path.exists()
    with open(ev_path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EVENT_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerows(sorted(new_events, key=lambda e: e["timestamp"]))

    print(f"Imported. Run scripts/render_tracker.py to see your pipeline, "
          f"or scripts/preflight.py to check everything.")


if __name__ == "__main__":
    main()
