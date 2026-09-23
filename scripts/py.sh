#!/usr/bin/env bash
# Run Python from the best available interpreter for the current directory:
# package .venv → repo-root .venv (npm run setup) → python3 on PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for candidate in "$PWD/.venv/bin/python" "$ROOT/.venv/bin/python"; do
  if [ -x "$candidate" ]; then
    exec "$candidate" "$@"
  fi
done
exec python3 "$@"
