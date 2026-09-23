#!/usr/bin/env bash
# Remove Python/test/build caches. Keeps .venv directories and node_modules.
set -euo pipefail
cd "$(dirname "$0")/.."

find . \
  \( -path ./node_modules -o -path '*/node_modules' -o -path ./.git -o -path '*/.venv' -o -path ./.venv-site \) -prune -o \
  \( -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache -o -name '*.egg-info' -o -name htmlcov \) \
     -o -type f \( -name '*.py[co]' -o -name .coverage -o -name coverage.xml \) \) \
  -print -exec rm -rf {} +

rm -rf site site-test-output packages/soulos-sdk/ts/dist
