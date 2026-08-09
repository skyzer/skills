"""Shared helpers: config loading, paths, event log, budgets.

Everything product-specific lives in config/. Nothing in scripts/ names a
company, market or product.
"""
import csv
import datetime as _dt
import json
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
    """Minimal .env loader so the scripts work without extra dependencies."""
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

CONFIG_DIR = ROOT / _env("CONFIG_DIR", "./config").lstrip("./")
STATE_DIR = ROOT / _env("STATE_DIR", "./state").lstrip("./")
RUNS_DIR = ROOT / _env("RUNS_DIR", "./runs").lstrip("./")

DRY_RUN = _env("DRY_RUN", "1") not in ("0", "false", "False", "")


_CONFIG_CACHE = {}

# Two files, split by who cares about them.
#
#   brief.md       the business: what you sell, who to, what you may claim, how
#                  you write. Markdown, read by the agent, never parsed here.
#                  (A structured brief.yaml also works and is merged if
#                  present, but it's optional.)
#   settings.yaml  the technical: which mail provider, which verifier, rate
#                  limits, and the copy numbers the send scripts enforce.
#
# They load into one dict, so callers don't need to know which file a key came
# from. The split is for the person, not the program.
CONFIG_FILES = ("brief.yaml", "settings.yaml")
OPTIONAL_CONFIG = {"brief.yaml"}


def _load_one(name):
    path = CONFIG_DIR / name
    if not path.exists():
        example = ROOT / "config.example" / name
        if example.exists():
            print(f"WARNING: using config.example/{name}. Copy config.example/ to config/ "
                  f"and fill it in before sending anything real.", file=sys.stderr)
            path = example
        elif name in OPTIONAL_CONFIG:
            return {}
        else:
            raise FileNotFoundError(f"No config file at {path}")
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def config(name=None):
    """Load the brief and the settings, merged into one dict.

    Pass a filename to load just one of them."""
    key = name or "__merged__"
    if key in _CONFIG_CACHE:
        return _CONFIG_CACHE[key]
    if name:
        _CONFIG_CACHE[key] = _load_one(name)
    else:
        merged = {}
        for fname in CONFIG_FILES:
            merged.update(_load_one(fname))
        _CONFIG_CACHE[key] = merged
    return _CONFIG_CACHE[key]


def cfg(dotted, default=None):
    """Read a nested value from either file: cfg("copy.max_words", 80)."""
    node = config()
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def cohort(abbr_or_name):
    """Look up a cohort by its short code or its name. The abbreviation is what
    goes in CSV columns, so it stays short and stable; the full text is what the
    agent reads to understand the group."""
    for c in config().get("cohorts") or []:
        if abbr_or_name in (c.get("abbr"), c.get("name")):
            return c
    return None


def state_path(name):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / name


def run_dir(run_id=None):
    run_id = run_id or _dt.date.today().isoformat()
    d = RUNS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------
# Events: append-only. Never edit or delete a row.
# --------------------------------------------------------------------------

EVENT_FIELDS = ["timestamp", "company", "domain", "person_email", "channel",
                "action", "detail", "run_id", "message_id"]

VALID_ACTIONS = {
    "sourced", "scored", "enriched", "skipped",
    "verified", "verify_failed", "excluded",
    "sent", "follow_up_sent", "bounced", "auto_replied",
    "reply_received", "reply_drafted", "reply_sent",
    "meeting_booked", "closed_won", "closed_lost", "not_interested",
    "do_not_contact", "needs_named_contact",
}


def append_event(company, action, domain="", person_email="", channel="email",
                 detail="", run_id="", message_id=""):
    """Append one event. Unknown actions are rejected: free-text status is how a
    tracker stops being countable."""
    if action not in VALID_ACTIONS:
        raise ValueError(
            f"Unknown action {action!r}. Use one of: {', '.join(sorted(VALID_ACTIONS))}. "
            f"Put nuance in `detail` instead of inventing an action.")
    path = state_path("events.csv")
    is_new = not path.exists()
    with open(path, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EVENT_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
            "company": company, "domain": domain, "person_email": person_email,
            "channel": channel, "action": action, "detail": detail,
            "run_id": run_id or _dt.date.today().isoformat(),
            "message_id": message_id,
        })


def read_events():
    path = state_path("events.csv")
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def sends_today():
    """Count sends today across all runs, for the daily cap."""
    today = _dt.date.today().isoformat()
    return sum(1 for e in read_events()
               if e["action"] in ("sent", "follow_up_sent")
               and e["timestamp"].startswith(today))


# --------------------------------------------------------------------------
# Exclusions: enforced, not advisory.
# --------------------------------------------------------------------------

def load_exclusions():
    path = state_path("exclusions.csv")
    if not path.exists():
        return {}
    with open(path, newline="") as fh:
        return {r["domain"].strip().lower(): r for r in csv.DictReader(fh) if r.get("domain")}


def excluded(email_or_domain):
    """Return the exclusion row if this address or domain is excluded, else None."""
    value = (email_or_domain or "").strip().lower()
    domain = value.split("@")[-1]
    ex = load_exclusions()
    return ex.get(domain) or ex.get(value)


# --------------------------------------------------------------------------
# Budgets: scarce resources with a remaining count.
# --------------------------------------------------------------------------

def load_budgets():
    path = state_path("budgets.yaml")
    if not path.exists():
        return {}
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def save_budgets(budgets):
    with open(state_path("budgets.yaml"), "w") as fh:
        yaml.safe_dump(budgets, fh, sort_keys=False)


def spend_budget(name, amount=1):
    """Decrement at the moment of use, not at the end of the run. A crashed run
    that already spent an invite must not spend it again."""
    budgets = load_budgets()
    if name not in budgets:
        return None
    remaining = budgets[name].get("remaining", 0)
    if remaining < amount:
        return False
    budgets[name]["remaining"] = remaining - amount
    save_budgets(budgets)
    return True


ROLE_LOCAL_PARTS = {
    "info", "support", "hello", "contact", "sales", "admin", "team", "help",
    "office", "partnerships", "compliance", "legal", "billing", "press",
    "media", "careers", "noreply", "no-reply", "enquiries", "inquiries",
    "general", "mail", "desk",
}


def is_role_address(email):
    local = (email or "").split("@")[0].strip().lower()
    return local in ROLE_LOCAL_PARTS


def looks_like_person(email):
    """firstname, firstname.lastname, f.lastname, firstnamelastname."""
    local = (email or "").split("@")[0].strip().lower()
    if not local or is_role_address(local):
        return False
    return local.replace(".", "").replace("-", "").replace("_", "").isalpha()
