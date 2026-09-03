"""Shared helpers for the scanner: paths, config, the two owned state files,
and read-only views of the files borrowed from the outbound skill.

Nothing in scripts/ names a company, market or product. Nothing in scripts/
can post, reply, DM or send email, and that is the point.
"""
import csv
import datetime as _dt
import hashlib
import os
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml. Run: pip install -r requirements.txt", file=sys.stderr)
    raise

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _env(key, default=None):
    return os.environ.get(key, default)


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_env()


def _resolve(value, default):
    raw = _env(value, default)
    p = pathlib.Path(raw)
    return p if p.is_absolute() else (ROOT / p).resolve()


CONFIG_DIR = _resolve("CONFIG_DIR", "./config")
STATE_DIR = _resolve("STATE_DIR", "./state")
RUNS_DIR = _resolve("RUNS_DIR", "./runs")

TODAY = _dt.date.today()


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

_SOURCES = None


def sources_config():
    """config/sources.yaml, falling back to the example with a warning."""
    global _SOURCES
    if _SOURCES is not None:
        return _SOURCES
    path = CONFIG_DIR / "sources.yaml"
    if not path.exists():
        example = ROOT / "config.example" / "sources.yaml"
        print("WARNING: using config.example/sources.yaml. Copy config.example/ to "
              "config/ and fill it in before trusting a scan.", file=sys.stderr)
        path = example
    with open(path) as fh:
        _SOURCES = yaml.safe_load(fh) or {}
    return _SOURCES


def threshold(name, default):
    return (sources_config().get("thresholds") or {}).get(name, default)


def enabled_sources():
    return {k: v for k, v in (sources_config().get("sources") or {}).items()
            if v and v.get("enabled")}


def brief_path():
    return CONFIG_DIR / "brief.md"


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

def state_path(name):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / name


def run_dir(run_id=None):
    d = RUNS_DIR / (run_id or TODAY.isoformat())
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------
# Owned state: signals.csv (rewritten per save) and seen_signals.csv (append)
# --------------------------------------------------------------------------

SIGNAL_FIELDS = [
    "id", "found_date", "source", "url", "author", "author_handle", "author_url",
    "company", "domain", "posted_date", "age_days", "text_excerpt", "problem",
    "intent_score", "confidence", "fit", "group", "status", "reasoning",
    "reply_draft", "dm_draft", "operator_note", "last_updated",
]

SIGNAL_STATUSES = {"new", "needs_review", "replied", "dm_sent",
                   "handed_to_outbound", "rejected", "expired"}

SEEN_FIELDS = ["id", "url", "seen_date", "outcome", "reason"]
SEEN_OUTCOMES = {"saved", "rejected", "duplicate", "too_old", "excluded",
                 "in_outbound_pipeline"}


def signal_id(url):
    return hashlib.sha1(url.strip().encode()).hexdigest()[:12]


def read_signals():
    path = state_path("signals.csv")
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def write_signals(rows):
    path = state_path("signals.csv")
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SIGNAL_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in SIGNAL_FIELDS})
    tmp.replace(path)


def read_seen():
    path = state_path("seen_signals.csv")
    if not path.exists():
        return {}
    with open(path, newline="") as fh:
        return {r["id"]: r for r in csv.DictReader(fh)}


def append_seen(url, outcome, reason=""):
    if outcome not in SEEN_OUTCOMES:
        raise ValueError(f"Unknown outcome {outcome!r}; use one of {sorted(SEEN_OUTCOMES)}")
    path = state_path("seen_signals.csv")
    is_new = not path.exists()
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SEEN_FIELDS)
        if is_new:
            w.writeheader()
        w.writerow({"id": signal_id(url), "url": url.strip(),
                    "seen_date": TODAY.isoformat(), "outcome": outcome, "reason": reason})


def append_rejection(section, line):
    """state/rejections.md: '## Signals' and '## Voice'. Read before scoring."""
    path = state_path("rejections.md")
    text = path.read_text() if path.exists() else "# Rejections\n\n## Signals\n\n## Voice\n"
    header = f"## {section}"
    if header not in text:
        text = text.rstrip("\n") + f"\n\n{header}\n"
    lines = text.split("\n")
    i = lines.index(header)
    end = len(lines)
    for j in range(i + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    section_lines = [l for l in lines[i + 1:end] if l.strip()]
    section_lines.append(f"- {TODAY.isoformat()} \u00b7 {line}")
    lines[i + 1:end] = [""] + section_lines + [""]
    path.write_text("\n".join(lines).rstrip("\n") + "\n")


# --------------------------------------------------------------------------
# Borrowed state (read-only): exclusions.csv, prospects.csv
# --------------------------------------------------------------------------

def load_exclusions():
    path = STATE_DIR / "exclusions.csv"
    if not path.exists():
        return {}
    with open(path, newline="") as fh:
        return {r["domain"].strip().lower(): r for r in csv.DictReader(fh) if r.get("domain")}


def excluded(domain):
    return load_exclusions().get((domain or "").strip().lower())


def outbound_domains():
    """Domains already in the outbound skill's pipeline. Never written here."""
    path = STATE_DIR / "prospects.csv"
    if not path.exists():
        return set()
    with open(path, newline="") as fh:
        return {r.get("domain", "").strip().lower() for r in csv.DictReader(fh)
                if r.get("domain")}


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------

def parse_date(value):
    """ISO date or datetime, or a unix timestamp. Returns a date or None."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return _dt.datetime.utcfromtimestamp(value).date()
    s = str(value).strip()
    if s.isdigit():
        return _dt.datetime.utcfromtimestamp(int(s)).date()
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def age_days(posted_date):
    d = parse_date(posted_date)
    return (TODAY - d).days if d else None
