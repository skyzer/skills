#!/usr/bin/env python3
"""Save, draft, update or reject a signal. The only writer of signals.csv.

Save a scored candidate (JSON on stdin or --json):
    python scripts/save_signal.py --json '{"url": "...", "source": "reddit", ...}'
    cat scored.jsonl | python scripts/save_signal.py --stdin

Attach drafts (written by the agent per references/reply-copy.md):
    python scripts/save_signal.py --draft <id> --reply "..." --dm "..."

Operator actions:
    python scripts/save_signal.py --status <id> replied
    python scripts/save_signal.py --reject <id> --reason "vendor employee"
    python scripts/save_signal.py --voice "operator cut the second paragraph"

Every save runs the guards the skill promises: dedupe against seen_signals.csv,
refuse excluded domains, flag domains already in the outbound pipeline, drop
anything older than max_age_days, and route low score or low confidence to
needs_review instead of drafting. Nothing here posts anything anywhere.
"""
import argparse
import datetime as _dt
import json
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (SIGNAL_FIELDS, SIGNAL_STATUSES, TODAY, read_signals, write_signals,
                    read_seen, append_seen, append_rejection, excluded, outbound_domains,
                    signal_id, threshold, age_days, sources_config)

REQUIRED = ("url", "source", "text_excerpt", "intent_score", "confidence", "fit")


def _int(v, name):
    try:
        i = int(v)
    except (TypeError, ValueError):
        raise SystemExit(f"{name} must be an integer 1-10, got {v!r}")
    if not 1 <= i <= 10:
        raise SystemExit(f"{name} must be 1-10, got {i}")
    return i


def _domain_from(row):
    d = (row.get("domain") or "").strip().lower()
    if d:
        return d
    for key in ("author_url", "company_url", "website"):
        m = re.search(r"https?://(?:www\.)?([^/\s]+)", row.get(key) or "")
        if m and not any(h in m.group(1) for h in ("reddit.com", "x.com", "twitter.com",
                                                   "github.com", "ycombinator.com",
                                                   "linkedin.com")):
            return m.group(1).lower()
    return ""


def save(row):
    for k in REQUIRED:
        if row.get(k) in (None, ""):
            raise SystemExit(f"missing {k}; a signal without it can't be scored honestly")
    url = row["url"].strip()
    sid = signal_id(url)
    seen = read_seen()
    if sid in seen:
        print(f"skip {sid}: already seen ({seen[sid]['outcome']})")
        return None

    score = _int(row["intent_score"], "intent_score")
    conf = _int(row["confidence"], "confidence")
    fit = row["fit"].strip().lower()
    if fit not in ("yes", "no", "unclear"):
        raise SystemExit("fit must be yes | no | unclear")
    age = age_days(row.get("posted_date"))
    max_age = int(threshold("max_age_days", 14))
    if age is None:
        raise SystemExit("posted_date missing or unparseable; recency is not optional")
    if age > max_age:
        append_seen(url, "too_old", f"{age} days")
        print(f"skip {sid}: {age} days old (max {max_age})")
        return None
    if fit == "no" or score < int(threshold("save_min_score", 5)):
        append_seen(url, "rejected", f"score {score} fit {fit}: {row.get('reasoning', '')[:120]}")
        print(f"reject {sid}: score {score}, fit {fit}")
        return None

    domain = _domain_from(row)
    ex = excluded(domain) if domain else None
    status = "new"
    note = row.get("operator_note", "")
    if ex and ex.get("scope") in ("never", "competitor"):
        append_seen(url, "excluded", f"{domain} scope {ex.get('scope')}")
        print(f"skip {sid}: {domain} is excluded ({ex.get('scope')})")
        return None
    if ex and ex.get("scope") == "no_cold":
        status, note = "needs_review", f"warm relationship ({ex.get('reason','')}); reply personally, no draft"
    if domain and domain in outbound_domains():
        status = "needs_review"
        note = (note + "; " if note else "") + "already in outbound pipeline; hand context to that sequence"
        append_seen(url, "in_outbound_pipeline", domain)
    else:
        append_seen(url, "saved", f"score {score}")
    if fit == "unclear" or conf < int(threshold("min_confidence", 5)) \
            or (row.get("problem") or "").strip().lower() in ("", "unknown"):
        status = "needs_review"

    rec = {k: row.get(k, "") for k in SIGNAL_FIELDS}
    rec.update({"id": sid, "url": url, "found_date": TODAY.isoformat(),
                "age_days": age, "intent_score": score, "confidence": conf, "fit": fit,
                "status": status, "operator_note": note,
                "last_updated": _dt.datetime.now().isoformat(timespec="seconds")})
    rec["text_excerpt"] = (rec["text_excerpt"] or "")[:300].replace("\n", " ")
    rows = read_signals()
    rows.append(rec)
    write_signals(rows)
    wants = []
    if status == "new":
        if score >= int(threshold("reply_min_score", 5)):
            wants.append("reply")
        if score >= int(threshold("dm_min_score", 7)):
            wants.append("dm")
    print(f"saved {sid}: score {score}/{conf} fit {fit} status {status}"
          + (f" -> draft {', '.join(wants)}" if wants else " -> no drafts"))
    return rec


def _check_draft(text, limit, allow_links, label):
    words = len(text.split())
    if limit and words > limit:
        raise SystemExit(f"{label}: {words} words, limit {limit}")
    if "—" in text or "–" in text:
        raise SystemExit(f"{label}: contains a dash; rewrite without it")
    if "!" in text:
        raise SystemExit(f"{label}: exclamation mark")
    if not allow_links and re.search(r"https?://", text):
        raise SystemExit(f"{label}: contains a link and this source does not allow one")
    banned = ("i hope this finds you well", "quick question", "leverage", "seamless",
              "robust", "cutting-edge", "game-changer", "i saw you were looking for",
              "we'd love to", "happy to help")
    low = text.lower()
    for b in banned:
        if b in low:
            raise SystemExit(f"{label}: banned phrase '{b}'")


def draft(sid, reply, dm):
    rows = read_signals()
    for r in rows:
        if r["id"] == sid:
            if r["status"] != "new":
                raise SystemExit(f"{sid} is {r['status']}; only 'new' signals get drafts")
            score = int(r["intent_score"])
            src = (sources_config().get("sources") or {}).get(r["source"]) or {}
            if reply:
                if score < int(threshold("reply_min_score", 5)):
                    raise SystemExit(f"score {score} is below reply_min_score")
                _check_draft(reply, int(src.get("reply_max_words", 120) or 0),
                             bool(src.get("allow_links")), "reply")
                r["reply_draft"] = reply
            if dm:
                if score < int(threshold("dm_min_score", 7)):
                    raise SystemExit(f"score {score} is below dm_min_score; no DM at this intent")
                _check_draft(dm, 80, False, "dm")
                r["dm_draft"] = dm
            r["last_updated"] = _dt.datetime.now().isoformat(timespec="seconds")
            write_signals(rows)
            print(f"drafted {sid}: " + ", ".join(x for x, v in (("reply", reply), ("dm", dm)) if v))
            return
    raise SystemExit(f"no signal {sid}")


def set_status(sid, status, note=""):
    if status not in SIGNAL_STATUSES:
        raise SystemExit(f"status must be one of {sorted(SIGNAL_STATUSES)}")
    rows = read_signals()
    for r in rows:
        if r["id"] == sid:
            r["status"] = status
            if note:
                r["operator_note"] = note
            r["last_updated"] = _dt.datetime.now().isoformat(timespec="seconds")
            write_signals(rows)
            print(f"{sid}: {status}")
            return
    raise SystemExit(f"no signal {sid}")


def reject(sid, reason):
    rows = read_signals()
    for r in rows:
        if r["id"] == sid:
            set_status(sid, "rejected", reason)
            append_rejection("Signals", f"{r['source']} · {r['url']} · \"{reason}\"")
            return
    raise SystemExit(f"no signal {sid}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--draft", metavar="ID")
    ap.add_argument("--reply")
    ap.add_argument("--dm")
    ap.add_argument("--status", nargs=2, metavar=("ID", "STATUS"))
    ap.add_argument("--note", default="")
    ap.add_argument("--reject", metavar="ID")
    ap.add_argument("--reason", default="")
    ap.add_argument("--voice", help="record a voice correction from the operator's edit")
    a = ap.parse_args()

    if a.json:
        save(json.loads(a.json))
    elif a.stdin:
        for line in sys.stdin:
            line = line.strip()
            if line:
                save(json.loads(line))
    elif a.draft:
        if not (a.reply or a.dm):
            ap.error("--draft needs --reply and/or --dm")
        draft(a.draft, a.reply, a.dm)
    elif a.status:
        set_status(a.status[0], a.status[1], a.note)
    elif a.reject:
        if not a.reason:
            ap.error("--reject needs --reason; the reason is what the correction loop learns from")
        reject(a.reject, a.reason)
    elif a.voice:
        append_rejection("Voice", a.voice)
        print("recorded voice note")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
