# SoulOS API Reference

REST endpoints, SSE multiplexing, and MCP tool exposure for SoulOS dual-process inference.

**OpenAPI (SDK contract):** live at `GET /openapi.json` and Swagger UI at `GET /docs` on the kernel. Committed artifact: [openapi.kernel.json](openapi.kernel.json) — regenerate with `npm run openapi:export`.

**Hybrid sidecar (primary):** [Hybrid API](hybrid-api.md) · [Identity model](../guides/identity-model.md)

**Errors:** All `4xx`/`5xx` responses use RFC 7807 Problem Details (`Content-Type: application/problem+json`) with fields `type`, `title`, `status`, `detail`, and extension `code` (e.g. `BOT_NOT_FOUND`, `INFERENCE_DOWN`, `READY_DEGRADED`, `SOUL_INVALID`, `MEMORY_DIM_MISMATCH`). Clients should key off `code`, not plain `detail` strings. Full hybrid examples: [hybrid-api.md](hybrid-api.md#errors-rfc-7807).

**Hybrid detail →** [hybrid-api.md](hybrid-api.md) (request/response JSON for `/hybrid/*`, `/ready`, `/v1/avatars/ensure`).

**Related:** [MCP guide](../guides/mcp.md) · [MCP tools](mcp-tools.md) · [Soul standard](soul-standard.md)

---

## 1. Data Structures

### Metacognitive State Vector (MSV)

The MSV tracks the avatar's internal psychological state. It is stored as `JSONB` in PostgreSQL (`bots.current_msv`). Personality traits use **HEXACO** (see [spec/soul.schema.json](../../spec/soul.schema.json)).

```json
{
  "hexaco": {
    "H": 0.85,
    "E": 0.40,
    "X": 0.72,
    "A": 0.90,
    "C": 0.50,
    "O": 0.65
  },
  "moral_foundations": {
    "care_harm": 0.9,
    "fairness_cheating": 0.8,
    "loyalty_betrayal": 0.7,
    "authority_subversion": 0.5,
    "sanctity_degradation": 0.4
  },
  "drives": {
    "curiosity": 0.6,
    "autonomy": 0.4,
    "social_approval": 0.7
  },
  "epistemic_uncertainty": 0.25,
  "inner_monologue": "I feel comfortable answering this question as it relates to my core knowledge."
}
```

HEXACO keys: **H** Honesty-Humility, **E** Emotionality, **X** eXtraversion, **A** Agreeableness, **C** Conscientiousness, **O** Openness (-1.0 to 1.0).

---

## 2. Server-Sent Events (SSE)

`POST /chat/generate` multiplexes System 1 text and System 2 MSV updates on one stream.

### Text generation (`message`)

```text
event: message
data: {"text": " Hello"}

event: message
data: {"text": " World"}
```

### Cognitive reflection (`msv_update`)

Fired once per turn when System 2 finishes; clients should handle it mid-stream without breaking text concatenation.

```text
event: msv_update
data: {"hexaco": {"H": 0.8, "E": 0.4, "X": 0.6, "A": 0.9, "C": 0.5, "O": 0.7}, "moral_foundations": {...}, "drives": {...}, "epistemic_uncertainty": 0.1, "inner_monologue": "The user is greeting me."}
```

### Cognitive telemetry (`cognitive_state`)

Emitted alongside `message` and `msv_update` for dual-process observability (Studio rails, SDK `event["type"] == "cognitive_state"`).

```text
event: cognitive_state
data: {
  "timestamp": 1781432100,
  "current_path": "system_2_deliberation",
  "system_1": {
    "confidence_score": 0.21,
    "cached_response_triggered": false,
    "latency_ms": 45
  },
  "system_2": {
    "loop_count": 1,
    "reasoning_tokens": 512,
    "active_mcp_tools": [],
    "latency_ms": 1120
  }
}
```

`confidence_score` is derived from `1 - epistemic_uncertainty`. When confidence falls below `dual_process.system1_threshold` from the soul's `runtime_config`, the stream signals `system_2_deliberation`.

**Payload:** `{"bot_id": "uuid", "message": "string"}`

---

## 3. MCP

Transport: HTTP SSE at `GET /mcp/sse` (see [MCP guide](../guides/mcp.md)).

| Tool | Purpose |
|------|---------|
| `ingest_memory` | Store episodic memory |
| `retrieve_memory` | Semantic recall (`query`, optional `top_k`) |
| `get_identity` | Persona + baseline/current MSV JSON |
| `register_avatar` | Create avatar from `.soul.json` object |
| `list_avatars` | List avatars (tenant-scoped when auth enabled) |
| `update_cognitive_state` | Force-update MSV |

Full argument schemas: [mcp-tools.md](mcp-tools.md).

Resources: `memory://episodic/{bot_id}`, `soul://identity/{bot_id}`. Prompt: `identity`.

**Not exposed via MCP:** `chat/generate` streaming — use REST or `@soulos/sdk`.

**REST-only in v0.2 (no MCP tool):** `POST /memory/forget` and `DELETE /memory/session/{bot_id}/{session_id}` — use REST or the SDK HTTP client.

---

## 4. REST Endpoints

Base URL (self-host): `http://localhost:8000`

### `POST /v1/avatars`

Register a new avatar from a **`.soul.json` object** or a raw **`.soul`** file body. Validates soul fields against [spec/soul.schema.json](../../spec/soul.schema.json).

- **JSON payload:** Full soul file (`name`, `role`, `description`, `attachment_style`, `baseline_msv`, optional marketplace fields). Optional `runtime_config` for `dual_process` thresholds.
- **`.soul` body:** `Content-Type: text/markdown` (or `application/octet-stream`) with `X-Filename: my-bot.soul` header; YAML front matter + Markdown body compiled server-side.
- **Success:** `200` with `{ "id", "name", "role", "baseline_msv", "current_msv" }` — `current_msv` is initialized from `baseline_msv`.
- **Validation error:** `422` RFC 7807 with `code: SOUL_INVALID` (and `detail` listing invalid traits).

### `POST /memory/ingest`

- **Payload:** `{"bot_id": "uuid", "content": "string", "session_id?": "string"}`
- **Response:** `{"status": "success"}`
- When `session_id` is set, the row is tagged for that session (see [session memory](../guides/session-memory.md)).

### `POST /memory/sync`

Hydrate pgvector from a workspace `.soul-memory/` directory (dedupes by content hash).

- **Payload:** `{"bot_id": "uuid", "workspace_path": "/path/to/project"}`
- **Response:** `{"status": "success", "imported": N, "skipped": N, "total": N}`

### `POST /memory/retrieve`

- **Payload:** `{"bot_id": "uuid", "query": "string", "top_k?": 5, "session_id?": "string"}`
- **Response:** `{"memories": ["string"]}`
- With `session_id`, retrieve merges global (`session_id IS NULL`) and session-scoped rows.

### `POST /memory/forget`

Content-match delete (ILIKE). **REST-only** — not exposed via MCP in v0.2.

- **Payload:** `{"bot_id": "uuid", "content_match": "string"}`
- **Response:** `{"status": "success", "deleted": N}`

### `DELETE /memory/session/{bot_id}/{session_id}`

Delete all memories for a session (GDPR / conversation teardown). Also deletes the matching `turn_sessions` row when turn contracts are in use. **REST-only** — not exposed via MCP in v0.2.

- **Response:** `{"status": "success", "deleted": N, "turn_sessions_deleted": N, "bot_id": "...", "session_id": "..."}`

### `POST /memory/purge-expired`

Delete **session-scoped** memories and expired `turn_sessions` older than `MEMORY_SESSION_TTL_SECONDS` (no-op when TTL is `0`). Global memory rows are never purged by this endpoint.

- **Payload:** `{"bot_id": "uuid"}` or `{}` to purge all bots (operator / CronJob; under tenant auth `bot_id` is required)
- **Response:** `{"status": "success", "deleted": N, "turn_sessions_deleted": N, "bot_id": "..."}`

### `POST /state/update`

- **Payload:** `{"bot_id": "uuid", "new_msv": { ... }}`
- **Response:** `{"status": "success", "message": "..."}`

### `POST /state/reflect`

Run System 2 reflector for hybrid integrations that skip `/chat/generate`.

- **Payload:** `{"bot_id": "uuid", "message": "string", "reflect_async": false}`
- **Response:** `{"status": "success", "bot_id": "...", "current_msv": { ... }, "latency_ms": N}`
- **Async:** `reflect_async: true` → `202` with `{"status": "accepted", "reflect": "async"}`

### `GET /ready`

Sidecar readiness probe (prefer over `/health` alone for `SOULOS_ENABLED` fallback).

- **200** — healthy JSON: `{ "status": "ok", "service": "soulos-kernel", "checks": { "database", "inference" }, "embedding_dimension", "inference_api_url" }`
- **503** — RFC 7807 `application/problem+json` with `code: "READY_DEGRADED"` when database or inference is unhealthy

Request/response detail: [hybrid-api.md](hybrid-api.md#get-ready).

### `POST /hybrid/prepare`

Single call for hybrid orchestrator pre-turn context.

- **Payload:** `{"bot_id", "query", "top_k?", "session_id?"}`
- **Response:** `identity`, `memories`, `system_prompt`, `inner_monologue`, optional `contract_context` when `runtime_config.turn_contract` is set and `session_id` is provided

### `POST /hybrid/complete`

Post-turn ingest + optional reflect. With an active turn contract, validates slots / advances the state machine before ingest.

- **Payload:** `{"bot_id", "summary", "user_message?", "session_id?", "reflect": true, "reflect_async": true, "filled_slots?", "intent?", "assistant_text?", "expected_version?", "idempotency_key?", "advance?", "expected_step?"}`
- **Response:** `200` with reflect result (and optional `turn`), or `202` when `reflect_async` is true; `404`/`409`/`422` for `TURN_*` codes (see [hybrid-api.md](hybrid-api.md))

### `POST /v1/avatars/ensure`

Idempotent avatar registration by `external_key`.

- **Payload:** `{"external_key": "string", "soul": { ... }, "runtime_config?": { ... }}`
- **Response:** same as `POST /v1/avatars`

`runtime_config.hybrid_prompt_template` — optional string template with `{name}`, `{role}`, `{description}`, `{inner_monologue}`, `{memories}`.  
`runtime_config.turn_contract` — optional turn contract (validated against [`spec/turn-contract.schema.json`](../../spec/turn-contract.schema.json)).

Hybrid prepare/complete JSON shapes: [hybrid-api.md](hybrid-api.md).

### `GET /bot/{bot_id}/identity`

- **Response:** `name`, `role`, `description`, `current_msv`.

### `GET /bot/{bot_id}/memories`

- **Query:** `?limit=50&session_id=` (optional session filter)
- **Response:** `{ "bot_id", "session_id", "memories": [...] }` — chronological episodic text chunks.

---

## 5. Errors (RFC 7807)

Every failed kernel response uses `Content-Type: application/problem+json`:

```json
{
  "type": "https://soulos.dev/problems/bot-not-found",
  "title": "Bot not found",
  "status": 404,
  "detail": "Bot not found: …",
  "code": "BOT_NOT_FOUND"
}
```

| `code` | Typical status | Meaning |
|--------|----------------|---------|
| `BOT_NOT_FOUND` | 404 | Unknown `bot_id` |
| `ACCESS_DENIED` | 403 | Tenant / auth gate |
| `SOUL_INVALID` | 422 | Soul schema validation failed |
| `INFERENCE_DOWN` | 503 | Inference / embedder unreachable |
| `MEMORY_DIM_MISMATCH` | 500 | Embedding dimension mismatch |
| `READY_DEGRADED` | 503 | `GET /ready` when checks fail |

Troubleshooting by `code`: [troubleshooting.md](../guides/troubleshooting.md).
