# Hybrid API (sidecar v0.2)

JSON shapes for `POST /hybrid/*`, `GET /ready`, and `POST /v1/avatars/ensure`. Full REST list: [api.md](api.md).

## `GET /ready`

**200** when database and inference are healthy; **503** when degraded.

```json
{
  "status": "ok",
  "service": "soulos-kernel",
  "checks": {
    "database": "ok",
    "inference": "ok"
  },
  "embedding_dimension": 768,
  "inference_api_url": "http://soulos-inference-bridge:11434"
}
```

Use for runtime `SOULOS_ENABLED` fallback (prefer over `/health` alone).

## `POST /v1/avatars/ensure`

Idempotent registration by `external_key` (per tenant / workspace / product).

**Request**

```json
{
  "external_key": "workspace:550e8400-e29b-41d4-a716-446655440000",
  "soul": { "name": "...", "role": "...", "baseline_msv": { ... } },
  "runtime_config": {
    "hybrid_prompt_template": "You are {name}...\n{memories}",
    "dual_process": { "system1_threshold": 0.35 }
  }
}
```

**Response** — same as `POST /v1/avatars`: `{ "id", "name", "role", "baseline_msv", "current_msv" }`

## `POST /hybrid/prepare`

Single pre-turn call (replaces `GET /bot/{id}/identity` + `POST /memory/retrieve`).

**Request**

```json
{
  "bot_id": "uuid",
  "query": "user message or search query",
  "top_k": 5,
  "session_id": "optional-session-uuid"
}
```

**Response**

```json
{
  "bot_id": "uuid",
  "identity": {
    "name": "string",
    "role": "string",
    "description": "string",
    "current_msv": { ... }
  },
  "memories": ["string", ...],
  "system_prompt": "ready-to-use system string",
  "inner_monologue": "string"
}
```

## `POST /hybrid/complete`

Post-turn ingest + optional MSV reflect.

**Request**

```json
{
  "bot_id": "uuid",
  "summary": "turn summary for episodic memory",
  "user_message": "original user message for reflect",
  "session_id": "optional-session-uuid",
  "reflect": true,
  "reflect_async": true
}
```

**Response**

- **200** — sync reflect: `{ "status": "success", "ingested": true, "reflect": "completed", "current_msv": { ... } }`
- **202** — async reflect: `{ "status": "accepted", "ingested": true, "reflect": "async", "bot_id": "uuid" }`
- **200** — `reflect: false`: `{ "status": "success", "ingested": true, "reflect": "skipped" }`

## Memory with `session_id`

`POST /memory/ingest` and `POST /memory/retrieve` accept optional `session_id`.

`GET /bot/{bot_id}/memories?session_id=` lists session-scoped rows.

## `POST /state/reflect` (legacy)

Still supported. Prefer `hybrid/complete` with `reflect_async: true`.

**Request:** `{ "bot_id", "message", "reflect_async": false }`

## Client libraries

| Language | Class |
|----------|--------|
| Python | `SoulHybridClient` from `soulos` |
| TypeScript | `SoulHybridClient` from `@soulos/sdk` |
