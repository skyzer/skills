#!/usr/bin/env bash
# Sets up config/ and .env from the examples, and optionally installs the skill.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "buyer-signal-scanner install"

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

if [ "${1:-}" = "--skill" ]; then
  DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/buyer-signal-scanner"
  mkdir -p "$DEST"
  cp -r skill/* "$DEST/"
  echo "  installed the skill to $DEST"
fi

cat <<'MSG'

Next:
  1. pip install -r requirements.txt
  2. Fill in config/brief.md and config/sources.yaml
     (or point CONFIG_DIR/STATE_DIR in .env at your outbound-master folders
      to share the brief, exclusions and prospect list)
  3. python scripts/preflight.py

This skill drafts. It has no send path, so there is nothing to switch off.
MSG
