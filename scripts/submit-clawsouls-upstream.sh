#!/usr/bin/env bash
# File the SoulOS framework request upstream (requires: gh auth login).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BODY_FILE="$ROOT/docs/upstream/clawsouls-framework-issue.md"

if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI: brew install gh && gh auth login" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Run: gh auth login" >&2
  exit 1
fi

# Strip YAML front matter (lines between --- markers)
BODY=$(awk 'BEGIN{p=0} /^---$/{p++; next} p>=2{print}' "$BODY_FILE")

gh issue create \
  --repo clawsouls/soulspec \
  --title "Add soulos to compatibility.frameworks" \
  --body "$BODY"

echo "Submitted to clawsouls/soulspec"
