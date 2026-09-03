#!/usr/bin/env python3
"""Run first, every time. Checks config, state and which sources this runtime
can reach, and says which ones need the browser. Exit 1 on anything that
would make a scan produce plausible nonsense.

Usage:
    python scripts/preflight.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (CONFIG_DIR, STATE_DIR, RUNS_DIR, ROOT, brief_path,
                    sources_config, enabled_sources, threshold, read_signals,
                    load_exclusions, outbound_domains)

problems, notes = [], []

# --- config
if not brief_path().exists():
    problems.append(f"No brief at {brief_path()}. Fill in config/brief.md or point "
                    "CONFIG_DIR at the outbound skill's config/.")
else:
    txt = brief_path().read_text()
    if "<One paragraph" in txt or "GRP1" in txt:
        problems.append("config/brief.md still has example placeholders.")

if not (CONFIG_DIR / "sources.yaml").exists():
    problems.append(f"No sources.yaml in {CONFIG_DIR}. Copy config.example/ to config/.")
else:
    srcs = enabled_sources()
    if not srcs:
        problems.append("No source is enabled in sources.yaml.")
    for name, s in srcs.items():
        qs = [q for q in (s.get("queries") or []) if "<" not in q]
        if not qs and s.get("access") != "browser":
            problems.append(f"source {name}: no real queries (placeholders still in place)")
        if len(qs) > 15:
            notes.append(f"source {name}: {len(qs)} queries; the reference says keep it under 15")
        if s.get("access") == "browser":
            notes.append(f"source {name}: browser only. Use the runtime's browser/web search "
                         f"with its query list; search.py will refuse it.")

# --- thresholds sanity
if threshold("dm_min_score", 7) < threshold("reply_min_score", 5):
    problems.append("dm_min_score is below reply_min_score; a DM is the bigger ask.")
if threshold("max_age_days", 14) > 30:
    notes.append("max_age_days > 30: signals that old are history, not intent.")

# --- credentials never in the repo
for p in ROOT.rglob("*"):
    if p.is_file() and p.suffix in (".json", ".pem", ".key") and "credential" in p.name.lower():
        if "config" not in p.parts and "state" not in p.parts:
            problems.append(f"credential-looking file outside config/: {p.relative_to(ROOT)}")
env = ROOT / ".env"
if env.exists():
    gi = (ROOT / ".gitignore").read_text() if (ROOT / ".gitignore").exists() else ""
    if ".env" not in gi:
        problems.append(".env exists but .gitignore does not list it.")

# --- state
STATE_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)
sig = read_signals()
open_new = sum(1 for r in sig if r.get("status") == "new")
review = sum(1 for r in sig if r.get("status") == "needs_review")
notes.append(f"state: {len(sig)} signals ({open_new} new, {review} needs_review) in {STATE_DIR}")
ex = load_exclusions()
notes.append(f"exclusions: {len(ex)} domains" if ex else
             "exclusions: none found (standalone mode; nothing shared with outbound)")
ob = outbound_domains()
if ob:
    notes.append(f"outbound pipeline: {len(ob)} domains visible for dedupe (read-only)")
if open_new > 40:
    notes.append(f"{open_new} signals waiting on the operator; consider a review before scanning more.")

# --- reachability (cheap HEADs; no retries)
try:
    import requests
    for name, url in (("hn", "https://hn.algolia.com/api/v1/search?query=test&hitsPerPage=1"),
                      ("github", "https://api.github.com/rate_limit"),
                      ("reddit", "https://www.reddit.com/search.json?q=test&limit=1")):
        if name not in enabled_sources():
            continue
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "buyer-signal-scanner preflight"})
            notes.append(f"reach {name}: HTTP {r.status_code}" +
                         ("" if r.ok else " (search.py will fall back to browser for this source)"))
        except Exception as e:  # noqa: BLE001
            notes.append(f"reach {name}: unreachable ({type(e).__name__})")
except ImportError:
    problems.append("Missing dependency: requests. Run: pip install -r requirements.txt")

# --- the guard that matters
SEND_MARKERS = ("smtp" + "lib", "messages()" + ".send", "twitter.com/2/" + "tweets",
                "reddit.com/api/" + "comment")
for p in (ROOT / "scripts").glob("*.py"):
    if p.name == "preflight.py":
        continue
    t = p.read_text()
    for bad in SEND_MARKERS:
        if bad in t:
            problems.append(f"{p.name} contains a send path ({bad}). This skill drafts only.")

print("buyer-signal-scanner preflight")
for n in notes:
    print("  note:", n)
for p in problems:
    print("  PROBLEM:", p)
if problems:
    print("FAILED. Fix the problems above; do not work around them.")
    sys.exit(1)
print("OK")
