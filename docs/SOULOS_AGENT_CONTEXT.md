# SoulOS — Agent context (compact)

> Index: repo root [`llms.txt`](https://raw.githubusercontent.com/mziqudhd92/soul-os/main/llms.txt) · [`llms-full.txt`](https://raw.githubusercontent.com/mziqudhd92/soul-os/main/llms-full.txt)

Open-source runtime for **persistent AI avatars**: validated **`.soul`** / `.soul.json` personality (HEXACO MSV), **pgvector episodic memory** (+ optional **`.soul-memory/`** git ledger), **dual-process chat** (System 1 text + System 2 `msv_update` + `cognitive_state` telemetry). Same kernel for support bots, dev twins, companions — only the soul file changes.

Full docs live in repo `docs/` · regenerate full dump: `python3 scripts/doc-gen/bundle_agent_context.py --full`

---

## URLs & ports

| Service | Self-host | Cloud |
|---------|-----------|-------|
| Kernel REST | `http://localhost:8000` | via gateway only |
| MCP (HTTP SSE) | `http://localhost:8000/mcp/sse` | `https://api.soulos.dev/mcp/sse` + `Authorization: Bearer <key>` |
| Soul Studio UI | `http://localhost:8765` | local dev tool |
| Gateway | — | `http://localhost:8080` (local cloud stack) |

Boot: `docker compose up --build` (kernel :8000, studio :8765, Postgres, Ollama).

---

## Pick your integration

| Use case | Use |
|----------|-----|
| Cursor / Claude IDE agent (memory, FAQ, identity) | **MCP** at `/mcp/sse` |
| App, site, Discord bot | **REST** or `@soulos/sdk` / `soulos-sdk` |
| Hand-tune `.soul.json` | **Soul Studio** (`pip install soulos-studio`) |

MCP does **not** expose chat streaming — use REST/SDK for `POST /chat/generate`.

---

## Quick workflow

```bash
# 1. Register soul (returns id = bot_id)
curl -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/support-bot/support-bot.soul.json

# 2. Ingest knowledge
curl -X POST http://localhost:8000/memory/ingest \
  -d '{"bot_id":"<id>","content":"Refunds within 30 days."}'

# 3. Chat (SSE)
curl -N -X POST http://localhost:8000/chat/generate \
  -d '{"bot_id":"<id>","message":"Can I get a refund?"}'
```

**Cursor MCP config** (`examples/mcp/cursor-mcp.json`):

```json
{ "mcpServers": { "soulos": { "url": "http://localhost:8000/mcp/sse" } } }
```

Cloud MCP: same path on gateway URL + Bearer API key.

---

## `.soul` and `.soul.json`

Schema for validated fields: `spec/soul.schema.json`. Register via `POST /v1/avatars` (JSON or raw `.soul` body), MCP `register_avatar`, or SDK `register_avatar("path.soul")`.

**`.soul`** — YAML front matter + Markdown body (`examples/support-bot/support-bot.soul`). Long HEXACO names map to `H,E,X,A,C,O`. Optional `psychology.dual_process` → `runtime_config.system1_threshold`.

**`.soul.json`** — legacy JSON (still fully supported):

```json
{
  "name": "Acme Support",
  "role": "Customer Support",
  "description": "Short policy-focused system behavior (not long FAQ — ingest those as memory).",
  "attachment_style": "Secure",
  "baseline_msv": {
    "hexaco": { "H": 0.9, "E": 0.4, "X": 0.5, "A": 0.9, "C": 0.85, "O": 0.5 },
    "moral_foundations": {
      "care_harm": 0.95, "fairness_cheating": 0.9,
      "loyalty_betrayal": 0.7, "authority_subversion": 0.5, "sanctity_degradation": 0.4
    },
    "drives": { "curiosity": 0.5, "autonomy": 0.3, "social_approval": 0.8 },
    "epistemic_uncertainty": 0.15,
    "inner_monologue": "Ready to help."
  }
}
```

| Field | Range |
|-------|--------|
| `attachment_style` | `Secure`, `Anxious-Preoccupied`, `Dismissive-Avoidant` |
| HEXACO `H,E,X,A,C,O` | -1.0 … 1.0 |
| moral_foundations, drives | 0.0 … 1.0 |
| `epistemic_uncertainty` | 0.0 … 1.0 (live MSV; escalate support if > 0.7) |

`current_msv` drifts per turn via System 2; `baseline_msv` is soul at registration.

**Trait cheat sheet:** H = honesty / anti-hallucination · A = agreeableness · C = structure · X = verbosity · E = emotional reactivity · O = creativity. Support bots: higher A, care_harm, H. Dev twins: higher C, authority_subversion, curiosity.

Example souls: `examples/support-bot/`, `examples/dev-twin/`, `examples/companion/`.

---

## REST API (`baseUrl` = kernel or gateway)

| Method | Path | Body / notes |
|--------|------|----------------|
| `POST` | `/v1/avatars` | Full soul JSON → `{ id, name, role, baseline_msv, current_msv }` |
| `POST` | `/memory/ingest` | `{ bot_id, content }` |
| `POST` | `/memory/sync` | `{ bot_id, workspace_path }` → hydrate from `.soul-memory/` |
| `POST` | `/memory/retrieve` | `{ bot_id, query, top_k? }` → `{ memories[] }` |
| `POST` | `/chat/generate` | `{ bot_id, message }` → **SSE** |
| `POST` | `/state/update` | `{ bot_id, new_msv }` |
| `GET` | `/bot/{bot_id}/identity` | name, role, description, current_msv |
| `GET` | `/bot/{bot_id}/memories` | `?limit=50` episodic log |

Validation errors on register: `422` with trait-level detail.

---

## SSE (`POST /chat/generate`)

| Event | Payload |
|-------|---------|
| `message` | `{"text": "..."}` — System 1 tokens (concatenate) |
| `msv_update` | Full MSV JSON — System 2 reflection (handle mid-stream) |
| `cognitive_state` | `current_path`, `system_1` (confidence, latency), `system_2` (loops, tokens, MCP tools) |

**CLI** (from `packages/soulos-core`): `soulos memory-append`, `memory-export`, `memory-sync <bot_id>`.

---

## MCP (server: `soulos-kernel`, transport: HTTP SSE)

| Tool | Args | Purpose |
|------|------|---------|
| `ingest_memory` | `bot_id`, `content` | Store episodic memory |
| `retrieve_memory` | `bot_id`, `query`, `top_k?` | Semantic recall |
| `get_identity` | `bot_id` | Persona + baseline/current MSV |
| `register_avatar` | `soul` (object) | Create avatar |
| `list_avatars` | `limit?` | List avatars (tenant-scoped if auth on) |
| `update_cognitive_state` | `bot_id`, `new_msv` | Force MSV update |

**Resources:** `memory://episodic/{bot_id}` · `soul://identity/{bot_id}`  
**Prompt:** `identity` (`bot_id`)  
**Responses:** JSON in `TextContent`.

Implementation: `packages/soulos-core/mcp_server.py`

---

## SDK (same API surface)

**TypeScript** (`@soulos/sdk`):

```typescript
import { SoulOSClient } from '@soulos/sdk';
const soul = new SoulOSClient({ baseUrl: 'http://localhost:8000' });
// Cloud: new SoulOSClient({ apiKey: process.env.SOULOS_API_KEY })
const { id } = await soul.registerAvatar(soulPayload);
await soul.ingestMemory(id, 'fact');
for await (const e of soul.sendMessage(id, 'hello')) {
  if (e.type === 'message') process.stdout.write(e.text);
}
```

**Python** (`pip install -e packages/soulos-sdk/python`):

```python
from soulos.client import SoulOSClient
soul = SoulOSClient(base_url="http://localhost:8000")
avatar = await soul.register_avatar("my-bot.soul.json")
async for event in soul.send_message(avatar["id"], "hello"):
    if event["type"] == "message": ...
```

---

## Monorepo (where code lives)

| Path | Role |
|------|------|
| `packages/soulos-core/` | Kernel FastAPI, `mcp_server.py`, `runtime/` pipeline |
| `packages/soulos-gateway/` | Cloud gateway (:8080), Bearer keys, MCP proxy |
| `packages/soulos-sdk/ts/` | `@soulos/sdk` |
| `packages/soulos-sdk/python/` | `soulos-sdk` |
| `packages/soulos-studio/` | Soul Builder UI (`soulos-studio` CLI) |
| `spec/soul.schema.json` | Soul validation contract |
| `examples/` | support-bot, dev-twin, companion, mcp |

**Runtime pipeline:** `embedder` → `memory` (recall) → `pipeline` (System 1 SSE) → `reflector` (System 2 MSV). Routes in `main.py`.

---

## Deployment & security

| Mode | Notes |
|------|--------|
| Self-host | `REQUIRE_AUTH=0` default — **local dev only**; do not expose :8000 publicly |
| Cloud | Gateway only; `REQUIRE_AUTH=1` on kernel; `sk_…` API keys → `account_id` tenant scope |

MCP and REST share privileges (memory ingest, avatar registration, MSV updates). Protect gateway keys. Studio (:8765) is not for public exposure without auth.

Local cloud stack: `docker compose -f docker-compose.cloud.yml up --build` · demo key in `packages/soulos-gateway/keys.example.json`.

---

## Common issues

| Problem | Fix |
|---------|-----|
| Connection refused :8000 | `docker compose up` |
| Empty replies | Ingest facts; check Ollama (`llama3`, `nomic-embed-text`) |
| Soul validation 422 | Match `spec/soul.schema.json` keys and ranges |
| MCP ingest fails | Embeddings need inference API / Ollama healthy |
