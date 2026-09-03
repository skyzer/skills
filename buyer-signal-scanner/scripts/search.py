#!/usr/bin/env python3
"""Search the programmatic sources. Prints candidates as JSON lines; it does
not score or save anything, that's the agent's job (scoring needs judgment)
and save_signal.py's job (saving needs the dedupe and exclusion checks).

Usage:
    python scripts/search.py hn "Ask HN payments Nigeria"
    python scripts/search.py github "CNY payout is:issue"
    python scripts/search.py reddit "pay supplier in China" --subreddits Nigeria,smallbusiness
    python scripts/search.py all                       # every enabled script source, every query
    python scripts/search.py all --out runs/2026-09-03/0-candidates.jsonl

Sources marked access: browser in sources.yaml are refused here. Use the
runtime's browser with the same query list, and hand the results to
save_signal.py by hand.

Rules baked in: one request per query, no retries on 403/429/captcha, results
older than max_age_days are dropped before printing, and every URL already in
seen_signals.csv is dropped too, so the agent only ever scores new things.
"""
import argparse
import html
import re
import datetime as _dt
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (enabled_sources, threshold, read_seen, signal_id, TODAY,
                    parse_date, run_dir)

try:
    import requests
except ImportError:
    print("Missing dependency: requests. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

UA = os.environ.get("REDDIT_USER_AGENT", "buyer-signal-scanner/0.1")
MAX_AGE = int(threshold("max_age_days", 14))
SINCE_TS = int(time.mktime((TODAY - _dt.timedelta(days=MAX_AGE)).timetuple()))


def _blocked(r, source):
    if r.status_code in (403, 429) or "captcha" in r.text[:2000].lower():
        print(f"BLOCKED {source}: HTTP {r.status_code}. Not retrying. Use the browser for this "
              f"source this run.", file=sys.stderr)
        return True
    return False


def _cand(source, url, text, author, posted, extra=None):
    d = parse_date(posted)
    age = (TODAY - d).days if d else None
    if age is None or age > MAX_AGE:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return {"source": source, "url": url, "text_excerpt": text[:300],
            "author_handle": author or "", "posted_date": d.isoformat(), "age_days": age,
            **(extra or {})}


def search_hn(query, limit=30):
    r = requests.get("https://hn.algolia.com/api/v1/search_by_date",
                     params={"query": query, "tags": "(story,comment)",
                             "numericFilters": f"created_at_i>{SINCE_TS}",
                             "hitsPerPage": limit},
                     timeout=15, headers={"User-Agent": UA})
    if _blocked(r, "hn"):
        return []
    r.raise_for_status()
    out = []
    for h in r.json().get("hits", []):
        url = f"https://news.ycombinator.com/item?id={h['objectID']}"
        text = h.get("title") or h.get("comment_text") or h.get("story_text") or ""
        c = _cand("hn", url, text, h.get("author"), h.get("created_at"),
                  {"thread_title": h.get("story_title") or h.get("title") or ""})
        if c:
            out.append(c)
    return out


def search_github(query, limit=30):
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    since = (TODAY - _dt.timedelta(days=MAX_AGE)).isoformat()
    q = query if "is:" in query else f"{query} is:issue"
    r = requests.get("https://api.github.com/search/issues",
                     params={"q": f"{q} created:>={since}", "sort": "created",
                             "order": "desc", "per_page": limit},
                     timeout=15, headers=headers)
    if _blocked(r, "github"):
        return []
    r.raise_for_status()
    out = []
    for it in r.json().get("items", []):
        c = _cand("github", it["html_url"], f"{it.get('title','')} — {it.get('body') or ''}",
                  (it.get("user") or {}).get("login"), it.get("created_at"),
                  {"author_url": (it.get("user") or {}).get("html_url", ""),
                   "repo": it.get("repository_url", "").split("/repos/")[-1]})
        if c:
            out.append(c)
    return out


def search_reddit(query, subreddits=None, limit=30):
    params = {"q": query, "sort": "new", "t": "month", "limit": limit}
    url = "https://www.reddit.com/search.json"
    if subreddits:
        params["q"] = f"{query} (" + " OR ".join(f"subreddit:{s}" for s in subreddits) + ")"
    r = requests.get(url, params=params, timeout=15, headers={"User-Agent": UA})
    if _blocked(r, "reddit"):
        return []
    r.raise_for_status()
    out = []
    for ch in r.json().get("data", {}).get("children", []):
        d = ch["data"]
        c = _cand("reddit", "https://www.reddit.com" + d.get("permalink", ""),
                  f"{d.get('title','')} — {d.get('selftext') or ''}",
                  d.get("author"), d.get("created_utc"),
                  {"author_url": f"https://www.reddit.com/user/{d.get('author','')}",
                   "subreddit": d.get("subreddit", ""), "num_comments": d.get("num_comments", 0)})
        if c:
            out.append(c)
    return out


SEARCHERS = {"hn": search_hn, "github": search_github, "reddit": search_reddit}


def run_one(source, query, cfg):
    if cfg.get("access") == "browser" or source not in SEARCHERS:
        print(f"{source}: browser-only source. Search it with the runtime's browser using "
              f"the query list in sources.yaml.", file=sys.stderr)
        return []
    try:
        if source == "reddit":
            return search_reddit(query, cfg.get("subreddits") or None)
        return SEARCHERS[source](query)
    except requests.RequestException as e:
        print(f"{source}: request failed ({e}). Not retrying.", file=sys.stderr)
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="hn | github | reddit | all")
    ap.add_argument("query", nargs="?")
    ap.add_argument("--subreddits", help="comma separated, reddit only")
    ap.add_argument("--out", help="write JSONL here as well as stdout")
    a = ap.parse_args()

    srcs = enabled_sources()
    seen = read_seen()
    jobs = []
    if a.source == "all":
        for name, cfg in srcs.items():
            if cfg.get("access") == "browser":
                print(f"{name}: browser-only, skipped here.", file=sys.stderr)
                continue
            for q in cfg.get("queries") or []:
                if "<" in q:
                    continue
                jobs.append((name, q, cfg))
    else:
        if not a.query:
            ap.error("query required unless source is 'all'")
        cfg = dict(srcs.get(a.source) or {"access": "script"})
        if a.subreddits:
            cfg["subreddits"] = a.subreddits.split(",")
        jobs.append((a.source, a.query, cfg))

    out_fh = open(a.out, "a") if a.out else None
    n_new = n_seen = 0
    printed = set()
    for source, query, cfg in jobs:
        for c in run_one(source, query, cfg):
            sid = signal_id(c["url"])
            if sid in seen or sid in printed:
                n_seen += 1
                continue
            printed.add(sid)
            c["id"] = sid
            c["query"] = query
            line = json.dumps(c, ensure_ascii=False)
            print(line)
            if out_fh:
                out_fh.write(line + "\n")
            n_new += 1
        time.sleep(1.5)  # be a polite client; rate limits are per-minute
    if out_fh:
        out_fh.close()
    print(f"# {n_new} new candidates, {n_seen} already seen, {len(jobs)} queries", file=sys.stderr)


if __name__ == "__main__":
    main()
