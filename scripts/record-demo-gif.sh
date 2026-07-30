#!/usr/bin/env bash
# Record docs/assets/demo-hybrid.gif from the simulated CLI demo.
# Requires: asciinema, agg (brew install asciinema agg)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p docs/assets

CAST="$ROOT/docs/assets/demo-hybrid.cast"
GIF="$ROOT/docs/assets/demo-hybrid.gif"

command -v asciinema >/dev/null || { echo "install asciinema" >&2; exit 1; }
command -v agg >/dev/null || { echo "install agg (asciinema gif generator)" >&2; exit 1; }

chmod +x scripts/demo-hybrid-cli.sh

echo "==> Recording asciinema cast ..."
# Quiet recording of the simulate demo (no Docker)
SCALE="${DEMO_SLEEP_SCALE:-0.85}"
asciinema rec "$CAST" \
  --overwrite \
  --cols 88 \
  --rows 28 \
  --title "SoulOS hybrid demo" \
  --command "env DEMO_SLEEP_SCALE=$SCALE ./scripts/demo-hybrid-cli.sh --simulate"

echo "==> Rendering GIF with agg ..."
agg \
  --font-size 14 \
  --speed 1.15 \
  --theme monokai \
  "$CAST" \
  "$GIF"

echo "==> Wrote $GIF"
ls -lh "$GIF" "$CAST"
