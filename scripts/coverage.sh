#!/usr/bin/env bash
# Enforce ≥85% line coverage on product packages (tests omitted).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Prefer repo-root .venv (has pytest-cov from npm run setup); fall back to PATH.
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY=python3
fi
FAIL_UNDER="${COV_FAIL_UNDER:-85}"

# Ensure pytest-cov is available.
"$PY" -c "import pytest_cov" 2>/dev/null || "$PY" -m pip install -q pytest-cov

run_pkg() {
  local dir="$1"
  shift
  echo ""
  echo "=== Coverage ${dir} (fail-under=${FAIL_UNDER}) ==="
  (
    cd "$dir"
    "$PY" -m pytest -q \
      --cov \
      --cov-config=.coveragerc \
      --cov-report=term-missing:skip-covered \
      --cov-fail-under="$FAIL_UNDER" \
      "$@"
  )
}

run_pkg packages/soulos-core -m "not integration" --ignore=test_integration_pg.py
run_pkg packages/soulos-gateway
run_pkg packages/soulos-inference-bridge
run_pkg packages/soulos-studio
run_pkg packages/soulos-sdk/python

echo ""
echo "All packages ≥${FAIL_UNDER}% coverage."
