#!/usr/bin/env python3
"""Run before anything else. Fails loudly rather than sending something wrong.

Usage:
    python scripts/preflight.py

Checks, in order:
  1. No credential-shaped strings in files git would track. This is the one that
     matters most: the whole point of the config/ split is that the repo can be
     public, and one API key in a tracked file undoes that permanently, because
     git history is forever.
  2. config/ exists and has the files the skill expects.
  3. Credentials referenced by .env actually exist.
  4. State files are readable and the status vocabulary is intact.
  5. Reports whether DRY_RUN is on, and how much of the daily cap is left.
"""
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (CONFIG_DIR, DRY_RUN, ROOT, STATE_DIR, VALID_ACTIONS,
                    cfg, read_events, sends_today)

SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API key"),
    (re.compile(r'"private_key"\s*:\s*"-----BEGIN'), "service account private key"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-style key"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
     "hardcoded credential"),
    (re.compile(r"(?i)secret=[A-Za-z0-9]{20,}"), "credential in a URL"),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
SKIP_FILES = {".env.example"}

REQUIRED_CONFIG = ["settings.yaml"]
# The brief can be markdown (canonical) or yaml (also supported); one must exist.
BRIEF_FILES = ["brief.md", "brief.yaml"]


def tracked_files():
    """Prefer git's view of what's tracked. Fall back to a walk that honours the
    obvious ignores."""
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout
        return [ROOT / p for p in out.splitlines() if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = []
        for path in ROOT.rglob("*"):
            if path.is_dir() or any(part in SKIP_DIRS for part in path.parts):
                continue
            rel = path.relative_to(ROOT)
            if rel.parts and rel.parts[0] in ("config", "state", "runs", ".env"):
                continue
            files.append(path)
        return files


def check_secrets():
    findings = []
    for path in tracked_files():
        if not path.exists() or path.name in SKIP_FILES:
            continue
        if path.suffix in (".png", ".jpg", ".xlsx", ".pdf", ".ico"):
            continue
        try:
            text = path.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern, label in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line = text[:match.start()].count("\n") + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}  {label}")
    return findings


def check_config():
    problems = []
    if not CONFIG_DIR.exists():
        return ["config/ does not exist. Run install.sh, or copy config.example/ to "
                "config/ and fill it in."]
    for name in REQUIRED_CONFIG:
        if not (CONFIG_DIR / name).exists():
            problems.append(f"config/{name} is missing")
    if not any((CONFIG_DIR / b).exists() for b in BRIEF_FILES):
        problems.append("no brief found: config/ needs brief.md (or brief.yaml). "
                        "The agent can't write emails about a product it hasn't been told about.")
    return problems


def check_credentials():
    problems = []
    sa = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not sa:
        problems.append("GOOGLE_SERVICE_ACCOUNT_FILE not set in .env")
    elif not pathlib.Path(sa).expanduser().exists():
        problems.append(f"service account file not found: {sa}")
    if not os.environ.get("SEND_AS"):
        problems.append("SEND_AS not set in .env")
    provider = os.environ.get("EMAIL_VERIFIER", "none").lower()
    if provider != "none" and not os.environ.get("EMAIL_VERIFIER_KEY"):
        problems.append(f"EMAIL_VERIFIER is {provider} but EMAIL_VERIFIER_KEY is empty. "
                        "Verification would silently fall back to an MX check.")
    research = cfg("providers.research.type") or "agent"
    if isinstance(research, str):
        research = [research]
    key_for = {"brave": "BRAVE_API_KEY", "perplexity": "PERPLEXITY_API_KEY"}
    for r in research:
        r = r.lower()
        if r in key_for and not os.environ.get(key_for[r]):
            problems.append(f"providers.research.type includes {r} but {key_for[r]} "
                            "is empty. Research would fail mid-run instead of at preflight.")
    return problems


def check_exclusions():
    """Cross-reference the exclusion list against real prospects.

    Two failure modes this catches, both silent otherwise. An exclusion that
    matches nothing is usually a typo in the domain, which means the company
    you meant to protect is still reachable. And an exclusion matching a live
    prospect is worth surfacing so you can see the list is actually doing work
    rather than sitting there decoratively."""
    import csv as _csv
    ex_path = STATE_DIR / "exclusions.csv"
    pr_path = STATE_DIR / "prospects.csv"
    if not ex_path.exists() or not pr_path.exists():
        return [], []

    with open(ex_path, newline="") as fh:
        exclusions = [r for r in _csv.DictReader(fh) if r.get("domain")]
    with open(pr_path, newline="") as fh:
        prospects = list(_csv.DictReader(fh))

    matched, orphans = [], []
    for ex in exclusions:
        domain = ex["domain"].strip().lower()
        hits = [p for p in prospects
                if domain and (domain in (p.get("domain") or "").lower()
                               or (p.get("company") or "").lower() == (ex.get("company") or "").lower())]
        if hits:
            matched.append((ex, hits))
        else:
            orphans.append(ex)
    return matched, orphans


def check_state():
    problems = []
    bad_actions = set()
    for event in read_events():
        if event.get("action") not in VALID_ACTIONS:
            bad_actions.add(event.get("action"))
    if bad_actions:
        problems.append(f"events.csv contains unknown actions: {sorted(bad_actions)}. "
                        f"Counts derived from the log will be wrong.")
    if not (STATE_DIR / "exclusions.csv").exists():
        problems.append("state/exclusions.csv is missing. Nothing is being excluded, "
                        "which means an existing customer could get a cold email.")
    return problems


def main():
    print("preflight")
    failed = False

    secrets = check_secrets()
    if secrets:
        failed = True
        print("\n  FAIL  credentials found in files that git would track:")
        for line in secrets:
            print(f"          {line}")
        print("        Move them to .env, rotate them, and confirm .gitignore covers "
              "the file. Assume anything committed is already public.")
    else:
        print("  ok    no credential-shaped strings in tracked files")

    for label, problems in (("config", check_config()),
                            ("credentials", check_credentials()),
                            ("state", check_state())):
        if problems:
            failed = True
            print(f"\n  FAIL  {label}:")
            for p in problems:
                print(f"          {p}")
        else:
            print(f"  ok    {label}")

    matched, orphans = check_exclusions()
    if matched or orphans:
        print(f"\n  exclusions: {len(matched)} matched to prospects, "
              f"{len(orphans)} matched nothing")
        for ex, hits in matched:
            names = ", ".join(sorted({h["company"] for h in hits})[:3])
            more = f" +{len(hits) - 3}" if len(hits) > 3 else ""
            print(f"          {ex['scope']:10s} {ex['domain']:28s} -> {names}{more}")
        for ex in orphans:
            print(f"          WARN  {ex['domain']:28s} matches no prospect. "
                  f"Typo, or they're not in the list yet.")

    cap = int(os.environ.get("DAILY_SEND_CAP", "200"))
    used = sends_today()
    print(f"\n  DRY_RUN={'on (nothing will send)' if DRY_RUN else 'OFF - THIS WILL SEND'}")
    print(f"  daily cap: {used}/{cap} used, {max(0, cap - used)} remaining")

    if failed:
        print("\npreflight failed. Fix the causes above rather than skipping this.")
        sys.exit(1)
    print("\npreflight passed.")


if __name__ == "__main__":
    main()
