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

## `GET /v1/soulpacks`

List first-party MIT [SoulPacks](../guides/persona-packs.md). Optional `?q=` filters by id, name, or tags.

**Response:** `{ "packs": […], "total": N }`

## `POST /v1/avatars/import-soulpack`

Compile a SoulPack from `packs/soulpacks/` (or `SOULPACKS_ROOT`). License must be `MIT`.

**Request**

```json
{
  "pack_id": "support-agent",
  "persist": true,
  "msv_preset": "support-agent"
}
```

- `persist: false` (alias `register`) — return `soul`, `external_key`, `warnings` without DB write
- `persist: true` — `ensure` with `external_key` default `soulos:{pack_id}@{version}`

Errors: `SOULPACK_NOT_FOUND` (404), `SOULPACK_LICENSE_REJECTED` / `SOULPACK_INVALID` (422).

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

`POST /memory/ingest` and `POST /memory/retrieve` accept optional `session_id`. When set on hybrid prepare/complete, retrieve merges global + session memories; ingest tags facts with that session.

`GET /bot/{bot_id}/memories?session_id=` lists session-scoped rows.

`DELETE /memory/session/{bot_id}/{session_id}` — delete all memories for a session.

`POST /memory/forget` — `{ "bot_id", "content_match" }` deletes rows matching content (ILIKE).

## Multi-agent handoff (Phase A)

Kernel still runs **one `bot_id` per turn**. For specialist transfer, the app:

1. `POST /hybrid/complete` on the current bot (same `session_id` as the thread).
2. `POST /memory/ingest` on the **next** bot with a handoff note and the same `session_id`.
3. `POST /hybrid/prepare` on the next `bot_id`.

SDK: `soulos.handoff_to`, `role_external_key`, `conversation_session_id`. Guide: [multi-agent-teams.md](../guides/multi-agent-teams.md). Example: [examples/multi-agent-handoff](../../examples/multi-agent-handoff/).

### `runtime_config.memory_policy` (stub)

Optional stub on bot `runtime_config`:

| Value | Intended behavior (v0.2 stub) |
|-------|-------------------------------|
| `summary_only` (default) | Complete ingests `summary` only |
| `user_and_assistant` | Future: ingest both user message and assistant reply |

Document policy in your app; kernel stores the key for forward compatibility.

## Errors (RFC 7807)

Failed requests return `Content-Type: application/problem+json`:

```json
{
  "type": "https://soulos.dev/problems/bot-not-found",
  "title": "Bot not found",
  "status": 404,
  "detail": "Bot not found: …",
  "code": "BOT_NOT_FOUND"
}
```

Common codes: `BOT_NOT_FOUND`, `ACCESS_DENIED`, `INFERENCE_DOWN`, `MEMORY_DIM_MISMATCH`, `SOUL_INVALID`, `READY_DEGRADED`.

OpenAPI: `/openapi.json` · committed artifact: [openapi.kernel.json](openapi.kernel.json)

## Observability

Hybrid prepare/complete emit OpenTelemetry spans when `OTEL_EXPORTER_OTLP_ENDPOINT` or `SOULOS_OTEL_ENABLED=1` is set. Compatible with Langfuse, Phoenix, Datadog OTLP ingest. Studio turn inspector exports prepare JSON/curl for local debugging only.

## `POST /state/reflect` (legacy)

Still supported. Prefer `hybrid/complete` with `reflect_async: true`.

**Request:** `{ "bot_id", "message", "reflect_async": false }`

## Client libraries

| Language | Class | Testing |
|----------|--------|---------|
| Python | `SoulHybridClient` from `soulos` — includes `run_turn()` | Covered in CI (`packages/soulos-sdk/python/tests/`) |
| TypeScript | `SoulHybridClient` from `@soulos/sdk` — includes `runTurn()` | API parity documented; dedicated test suite tracked as a follow-up |
