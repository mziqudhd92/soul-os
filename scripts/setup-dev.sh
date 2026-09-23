#!/usr/bin/env bash
# One-shot contributor setup: repo-root .venv with every Python package (editable) + npm workspaces.
# Mirrors the CI install step so `npm run test:all` behaves the same locally.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "SoulOS needs Python 3.12+ (found: $("$PYTHON" --version 2>&1)). Set PYTHON=/path/to/python3.12." >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install \
  -e "packages/soulos-core[dev]" \
  -e "packages/soulos-gateway[dev]" \
  -e "packages/soulos-studio[dev]" \
  -e "packages/soulos-inference-bridge[dev]" \
  -e "packages/soulos-sdk/python[dev]" \
  ruff pytest-cov

npm install

echo "Setup complete. Run: npm run test:all"
