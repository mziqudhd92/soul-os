#!/usr/bin/env bash
# SoulOS hybrid CLI demo — for README recording and local tryouts.
#
#   ./scripts/demo-hybrid-cli.sh --simulate   # no Docker (good for asciinema/gif)
#   ./scripts/demo-hybrid-cli.sh               # hits a running kernel
#
# Record a GIF (requires asciinema + agg):
#   ./scripts/record-demo-gif.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

KERNEL="${SOULOS_KERNEL_URL:-http://localhost:8001}"
PACK_ID="${SOULOS_DEMO_PACK:-tutor}"
QUERY="${SOULOS_DEMO_QUERY:-Explain photosynthesis in one short paragraph for a 12-year-old.}"
SIMULATE=0
SLEEP_SCALE="${DEMO_SLEEP_SCALE:-1}"

for arg in "$@"; do
  case "$arg" in
    --simulate|-s) SIMULATE=1 ;;
    --help|-h)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

say() { printf '%s\n' "$*"; }
pause() {
  python3 -c "import time; time.sleep(float('$1') * float('$SLEEP_SCALE'))"
}
type_line() {
  local line="$1"
  local i
  for ((i = 0; i < ${#line}; i++)); do
    printf '%s' "${line:$i:1}"
    sleep 0.012
  done
  printf '\n'
}

banner() {
  say ""
  printf '\033[1;36m╔══════════════════════════════════════════════════════╗\033[0m\n'
  printf '\033[1;36m║  \033[1;37mSoulOS\033[0;36m  · identity + memory sidecar               \033[1;36m║\033[0m\n'
  printf '\033[1;36m╚══════════════════════════════════════════════════════╝\033[0m\n'
  say ""
}

step() {
  say ""
  printf '\033[1;33m→ \033[1;37m%s\033[0m\n' "$1"
}

ok() {
  printf '\033[1;32m  ✓ \033[0m%s\n' "$1"
}

dim() {
  printf '\033[0;90m  %s\033[0m\n' "$*"
}

banner
dim "ensure → prepare → your LLM → complete"
pause 0.6

step "1) Import a SoulPack (persona package)"
type_line "\$ curl -s -X POST \$KERNEL/v1/avatars/import-soulpack \\"
type_line "    -H 'content-type: application/json' \\"
type_line "    -d '{\"pack_id\":\"$PACK_ID\",\"persist\":true}'"

if [[ "$SIMULATE" -eq 1 ]]; then
  pause 0.4
  BOT_ID="demo-bot-tutor-7f3a"
  ok "imported pack_id=$PACK_ID  bot_id=$BOT_ID"
  dim "role: Tutor / Teacher · license: MIT · source: packs/soulpacks/$PACK_ID"
else
  RESP=$(curl -sf -X POST "$KERNEL/v1/avatars/import-soulpack" \
    -H "content-type: application/json" \
    -d "{\"pack_id\":\"$PACK_ID\",\"persist\":true}")
  BOT_ID=$(printf '%s' "$RESP" | python3 -c "import sys,json; b=json.load(sys.stdin); print(b.get('id') or b.get('bot_id') or '')")
  if [[ -z "$BOT_ID" ]]; then
    echo "import-soulpack did not return bot id (is the kernel up?)" >&2
    echo "$RESP" >&2
    exit 1
  fi
  ok "imported pack_id=$PACK_ID  bot_id=$BOT_ID"
fi
pause 0.5

step "2) Prepare turn — SoulOS builds system_prompt + memories"
type_line "\$ curl -s -X POST \$KERNEL/hybrid/prepare -d '{...query...}'"
pause 0.35

if [[ "$SIMULATE" -eq 1 ]]; then
  SYSTEM_PROMPT="You are Sage, a patient tutor. Explain ideas in clear steps, check understanding, and adapt difficulty. Inner monologue: Meet them at their level."
  ok "prepare OK — system_prompt ready for your LLM"
else
  PREPARE=$(curl -sf -X POST "$KERNEL/hybrid/prepare" \
    -H "content-type: application/json" \
    --data-binary @<(BOT="$BOT_ID" Q="$QUERY" python3 -c "import json,os; print(json.dumps({'bot_id':os.environ['BOT'],'query':os.environ['Q'],'top_k':3}))"))
  SYSTEM_PROMPT=$(printf '%s' "$PREPARE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('system_prompt',''))")
  ok "prepare OK — system_prompt ready for your LLM"
fi

say ""
printf '\033[0;36m  ┌─ system_prompt (excerpt) ─────────────────────────\033[0m\n'
printf '%s' "$SYSTEM_PROMPT" | head -c 420
say ""
printf '\033[0;36m  └──────────────────────────────────────────────────\033[0m\n'
pause 0.7

step "3) Your LLM generates (SoulOS stays on the sidecar)"
dim "Bedrock · OpenAI · LiteLLM · local models — your choice"
pause 0.35
REPLY="Photosynthesis is how plants make food from sunlight: they take in water and carbon dioxide, and release oxygen we can breathe."
printf '\033[1;35m  LLM → \033[0m%s\n' "$REPLY"
pause 0.55

step "4) Complete turn — ingest memory + optional MSV reflect"
type_line "\$ curl -s -X POST \$KERNEL/hybrid/complete -d '{...summary...}'"
pause 0.3

if [[ "$SIMULATE" -eq 1 ]]; then
  ok "complete OK — turn saved to episodic memory"
else
  curl -sf -X POST "$KERNEL/hybrid/complete" \
    -H "content-type: application/json" \
    --data-binary @<(BOT="$BOT_ID" REPLY="$REPLY" Q="$QUERY" python3 -c "
import json, os
print(json.dumps({
  'bot_id': os.environ['BOT'],
  'summary': os.environ['REPLY'][:500],
  'user_message': os.environ['Q'],
  'reflect': False,
}))
") >/dev/null
  ok "complete OK — turn saved to episodic memory"
fi
pause 0.45

say ""
printf '\033[1;32m══════════════════════════════════════════════════════\033[0m\n'
printf '\033[1;37m  Demo complete.\033[0m\n'
printf '\033[0;37m  Browse SoulPacks:  https://mziqudhd92.github.io/soul-os/soulpacks/\033[0m\n'
printf '\033[0;37m  Try live:          docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d\033[0m\n'
printf '\033[0;37m                     ./scripts/demo-hybrid-cli.sh\033[0m\n'
printf '\033[1;32m══════════════════════════════════════════════════════\033[0m\n'
say ""
