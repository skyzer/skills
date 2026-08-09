#!/usr/bin/env bash
# Sets up config/ and .env from the examples, and optionally installs the skill.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "outbound-master install"

if [ -d config ]; then
  echo "  config/ exists, leaving it alone"
else
  cp -r config.example config
  echo "  created config/ from config.example/"
fi

if [ -f .env ]; then
  echo "  .env exists, leaving it alone"
else
  cp .env.example .env
  echo "  created .env from .env.example"
fi

mkdir -p state runs
if [ ! -f state/exclusions.csv ]; then
  cp config.example/exclusions.csv state/exclusions.csv
  echo "  seeded state/exclusions.csv (replace the example rows)"
fi
if [ ! -f state/budgets.yaml ]; then
  cp config.example/budgets.yaml state/budgets.yaml
  echo "  seeded state/budgets.yaml"
fi

if [ "${1:-}" = "--skill" ]; then
  DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/outbound-master"
  mkdir -p "$DEST"
  cp -r skill/* "$DEST/"
  echo "  installed the skill to $DEST"
fi

cat <<'MSG'

Next:
  1. pip install -r requirements.txt
  2. Fill in config/brief.md and config/settings.yaml
  3. Put credentials in .env  (it is gitignored; never commit it)
  4. python scripts/preflight.py

DRY_RUN=1 is the default. Nothing sends until you turn it off, which you should
not do until a few full dry runs stop surprising you.
MSG
