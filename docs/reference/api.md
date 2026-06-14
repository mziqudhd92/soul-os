# SoulOS API Reference

REST endpoints, SSE multiplexing, and MCP tool exposure for SoulOS dual-process inference.

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

---

## 4. REST Endpoints

Base URL (self-host): `http://localhost:8000`

### `POST /v1/avatars`

Register a new avatar from a **`.soul.json` object** or a raw **`.soul`** file body. Validates soul fields against [spec/soul.schema.json](../../spec/soul.schema.json).

- **JSON payload:** Full soul file (`name`, `role`, `description`, `attachment_style`, `baseline_msv`, optional marketplace fields). Optional `runtime_config` for `dual_process` thresholds.
- **`.soul` body:** `Content-Type: text/markdown` (or `application/octet-stream`) with `X-Filename: my-bot.soul` header; YAML front matter + Markdown body compiled server-side.
- **Success:** `200` with `{ "id", "name", "role", "baseline_msv", "current_msv" }` — `current_msv` is initialized from `baseline_msv`.
- **Validation error:** `422` with a human-readable detail string listing each invalid trait.

### `POST /memory/ingest`

- **Payload:** `{"bot_id": "uuid", "content": "string"}`
- **Response:** `{"status": "success"}`

### `POST /memory/sync`

Hydrate pgvector from a workspace `.soul-memory/` directory (dedupes by content hash).

- **Payload:** `{"bot_id": "uuid", "workspace_path": "/path/to/project"}`
- **Response:** `{"status": "success", "imported": N, "skipped": N, "total": N}`

### `POST /memory/retrieve`

- **Payload:** `{"bot_id": "uuid", "query": "string", "top_k": 5}`
- **Response:** `{"memories": ["string"]}`

### `POST /state/update`

- **Payload:** `{"bot_id": "uuid", "new_msv": { ... }}`
- **Response:** `{"status": "success", "message": "..."}`

### `POST /state/reflect`

Run System 2 reflector for hybrid integrations that skip `/chat/generate`.

- **Payload:** `{"bot_id": "uuid", "message": "string"}`
- **Response:** `{"status": "success", "bot_id": "...", "current_msv": { ... }, "latency_ms": N}`

### `GET /bot/{bot_id}/identity`

- **Response:** `name`, `role`, `description`, `current_msv`.

### `GET /bot/{bot_id}/memories`

- **Query:** `?limit=50`
- **Response:** Chronological array of episodic text chunks.
