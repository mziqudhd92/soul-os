#!/usr/bin/env bash
# Fetch ClawSouls personas and convert to SoulOS .soul.json locally.
# Output is derivative work — see ATTRIBUTION.md and upstream license per soul.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
PY="${ROOT}/packages/soulos-core/.venv/bin/python"
SCRIPT="${ROOT}/scripts/clawsouls_to_soul.py"
OUT="${ROOT}/examples/clawsouls"

if [[ ! -x "$PY" ]]; then
  echo "Missing venv: ${PY}" >&2
  echo "Create with: cd packages/soulos-core && python3 -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 1
fi

for soul in surgical-coder minimalist devops-veteran; do
  "$PY" "$SCRIPT" "clawsouls/${soul}" -o "${OUT}/${soul}.soul.json"
done

cat <<EOF

Generated ${OUT}/*.soul.json (derivative works).
Do not redistribute without complying with each soul's SPDX license.
See ${OUT}/ATTRIBUTION.md

EOF
