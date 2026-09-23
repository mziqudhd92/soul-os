#!/usr/bin/env bash
# Pin runtime deps for Docker (no pytest / dev extras).
# Usage: bash scripts/compile-requirements.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  COMPILE=(uv pip compile)
elif command -v pip-compile >/dev/null 2>&1; then
  COMPILE=(pip-compile)
else
  echo "Need uv or pip-compile (pip-tools) to generate requirements.txt" >&2
  exit 1
fi

for pkg in packages/soulos-core packages/soulos-gateway; do
  echo "Compiling $pkg/requirements.txt ..."
  (cd "$pkg" && "${COMPILE[@]}" pyproject.toml -o requirements.txt)
done

echo "Done. Commit the updated requirements.txt files with Dockerfile changes."
