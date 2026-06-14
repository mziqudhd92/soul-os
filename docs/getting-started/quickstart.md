# 15-Minute Quickstart: Support Agent vs Dev Twin

**Level:** beginner · **Outcome:** two working avatars on one kernel — you will see how **only the soul file and memory** change behavior.

SoulOS uses **one kernel** for every avatar type. Same Postgres, same inference, same API — different **`.soul`** / `.soul.json` + different ingested facts or **`.soul-memory/`** ledger.

**Recommended if you write Python bots:** start with [Python bot integration](../guides/python-bot.md) instead — this quickstart is ideal for **curl / API exploration**.

> **Interactive terminal (recommended):** [Browse online](https://mziqudhd92.github.io/soul-os/?tutorial=quickstart) — simulated shell with typing animation, Path A + Path B.

## Prerequisites

```bash
git clone https://github.com/mziqudhd92/soul-os.git && cd soul-os
docker compose up --build
```

| Service | URL |
|---------|-----|
| Kernel | http://localhost:8000 |
| Studio (optional) | http://localhost:8765 |

Verify kernel:

```bash
curl -s http://localhost:8000/health || curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

---

<a id="path-a"></a>

## Path A — Support agent (~10 minutes)

**Goal:** customer-support avatar that knows refund policy from **memory**, not from a giant system prompt.

### A1 — Register the soul

**Option 1 — `.soul` (recommended):**

```bash
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: text/markdown" \
  -H "X-Filename: support-bot.soul" \
  --data-binary @examples/support-bot/support-bot.soul | tee /tmp/support-register.json
```

**Option 2 — `.soul.json`:**

```bash
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/support-bot/support-bot.soul.json | tee /tmp/support-register.json
```

**Expected:** JSON with `id`, `name`, `baseline_msv`, `current_msv`.

```bash
export SUPPORT_ID=$(python3 -c "import json; print(json.load(open('/tmp/support-register.json'))['id'])")
echo "bot_id=$SUPPORT_ID"
```

**If 422:** soul JSON failed validation — compare with [spec/soul.schema.json](../../spec/soul.schema.json).

### A2 — Ingest policy (episodic memory)

```bash
curl -X POST http://localhost:8000/memory/ingest \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$SUPPORT_ID\",\"content\":\"Full refunds within 30 days of purchase.\"}"
```

**Expected:** `{"status":"success"}` (or similar).

Ingest more lines from [examples/support-bot/faq.md](../../examples/support-bot/faq.md) for richer answers.

### A3 — Chat with SSE

```bash
curl -N -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$SUPPORT_ID\",\"message\":\"Can I get a refund after 20 days?\"}"
```

**Expected output pattern:**

```text
event: message
data: {"text":"..."}

event: message
data: {"text":"..."}

event: msv_update
data: {"hexaco":{...},"epistemic_uncertainty":0.2,...}

event: cognitive_state
data: {"current_path":"system_1_heuristic","system_1":{"confidence_score":0.85,...}}
```

The reply should mention **30 days** because memory was recalled — not because you pasted FAQ into the soul file.

### A3b — Git memory ledger (optional)

```bash
soulos memory-sync "$SUPPORT_ID" --workspace examples/support-bot
# or: curl -X POST http://localhost:8000/memory/sync \
#   -d "{\"bot_id\":\"$SUPPORT_ID\",\"workspace_path\":\"examples/support-bot\"}"
```

Commit `.soul-memory/` to git; sync after clone hydrates pgvector.

### A4 — Sanity check (optional)

```bash
curl -s -X POST http://localhost:8000/memory/retrieve \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$SUPPORT_ID\",\"query\":\"refund policy\",\"top_k\":3}"
```

You should see your ingested line in `memories`.

---

## Path B — Dev twin (~10 minutes)

**Goal:** developer assistant with **repo facts** in memory — same kernel, different soul.

### B1 — Register dev twin soul

```bash
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/dev-twin/dev-twin.soul.json | tee /tmp/dev-register.json

export DEV_ID=$(python3 -c "import json; print(json.load(open('/tmp/dev-register.json'))['id'])")
```

### B2 — Ingest technical context

```bash
curl -X POST http://localhost:8000/memory/ingest \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$DEV_ID\",\"content\":\"POST /v1/avatars registers avatars with validated HEXACO MSV and returns an id.\"}"
```

### B3 — Ask a dev question

```bash
curl -N -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$DEV_ID\",\"message\":\"How do I register a new avatar?\"}"
```

Compare tone and structure to Path A — **same API**, different personality baseline and memory.

---

## What you proved

| Concept | Path A | Path B |
|---------|--------|--------|
| Soul file | `support-bot.soul.json` | `dev-twin.soul.json` |
| Memory | FAQ / policy | API / repo facts |
| `bot_id` | `$SUPPORT_ID` | `$DEV_ID` |
| Kernel | Same `:8000` | Same `:8000` |

---

## TypeScript SDK (same runtime)

```typescript
import { SoulOSClient } from '@soulos/sdk';
import { registerAvatarFromFile } from '@soulos/sdk/node';

const soul = new SoulOSClient({ baseUrl: 'http://localhost:8000' });
const { id } = await registerAvatarFromFile(soul, './examples/support-bot/support-bot.soul.json');
await soul.ingestMemory(id, 'Full refunds within 30 days.');

for await (const event of soul.sendMessage(id, 'I need a refund')) {
  if (event.type === 'message') process.stdout.write(event.text);
}
```

## Hosted API

```typescript
const soul = new SoulOSClient({ apiKey: process.env.SOULOS_API_KEY });
```

Only client config changes — not your app logic.

---

## Soul Studio (visual path)

http://localhost:8765 — Wizard, sliders, **Deploy to kernel**, live chat. See [Soul Builder](soul-builder.md) and Studio tutorials.

## MCP (5 minutes)

`http://localhost:8000/mcp/sse` — [examples/mcp](../../examples/mcp/README.md) · [MCP guide](../guides/mcp.md)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Connection refused | `docker compose up` — wait for kernel |
| Empty / generic answers | Ingest memory; check Ollama (`llama3`) |
| No SSE output | Use `curl -N`; check `bot_id` |
| Slow first reply | Ollama model pull on first run |

---

## Next steps

- **[Python bot integration](../guides/python-bot.md)** — recommended for real bots
- [Soul standard](../reference/soul-standard.md) — `.soul.json` fields
- [API reference](../reference/api.md) — REST + SSE
- [Deployment](../deployment/README.md) — self-host vs Cloud
