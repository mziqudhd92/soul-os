#!/usr/bin/env bash
# Hybrid sidecar smoke: ensure avatar → doctor → prepare → print system_prompt
set -euo pipefail

KERNEL="${SOULOS_KERNEL_URL:-http://localhost:8001}"
INFERENCE="${INFERENCE_API_URL:-http://localhost:11434}"
EMBED_DIM="${EMBEDDING_DIMENSION:-768}"
SOUL_FILE="${SOULOS_SMOKE_SOUL:-examples/support-bot/support-bot.soul.json}"
EXTERNAL_KEY="${SOULOS_EXTERNAL_KEY:-smoke-test-bot}"
QUERY="${SOULOS_SMOKE_QUERY:-What is the refund policy?}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$SOUL_FILE" ]]; then
  echo "Soul file not found: $SOUL_FILE" >&2
  exit 1
fi

echo "==> Ensuring avatar (external_key=$EXTERNAL_KEY) ..."
ENSURE_RESP=$(curl -sf -X POST "$KERNEL/v1/avatars/ensure" \
  -H "Content-Type: application/json" \
  -d "{\"external_key\":\"$EXTERNAL_KEY\",\"soul\":$(cat "$SOUL_FILE")}")

BOT_ID=$(echo "$ENSURE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "    bot_id=$BOT_ID"

echo "==> Running doctor ..."
python3 scripts/soulos-doctor.py \
  --kernel "$KERNEL" \
  --inference "$INFERENCE" \
  --embedding-dimension "$EMBED_DIM" \
  --bot-id "$BOT_ID"

echo "==> hybrid/prepare ..."
PREPARE_RESP=$(curl -sf -X POST "$KERNEL/hybrid/prepare" \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT_ID\",\"query\":\"$QUERY\",\"top_k\":3}")

SYSTEM_PROMPT=$(echo "$PREPARE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['system_prompt'])")

echo ""
echo "=== system_prompt (first 800 chars) ==="
echo "$SYSTEM_PROMPT" | head -c 800
echo ""
echo "=== hybrid smoke OK ==="
