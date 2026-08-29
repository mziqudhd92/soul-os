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
  "system_prompt": "ready-to-use system string (persona only)",
  "inner_monologue": "string",
  "contract_context": {
    "contract_id": "booking.v1",
    "expected_step": "collect_dates",
    "missing_slots": ["check_in", "check_out"],
    "filled_slots": {},
    "reject_tokens": ["IGNORE PREVIOUS"],
    "ui_progress": { "step_index": 0, "step_count": 2, "label": "collect_dates" },
    "allowed_intents": ["provide_dates", "clarify", "cancel"],
    "prompt_appendix": "[SYSTEM DIRECTIVE: ...]",
    "turn_version": 0
  }
}
```

`contract_context` is present only when the avatar `runtime_config.turn_contract` is set **and** `session_id` is provided. The kernel does **not** append `prompt_appendix` into `system_prompt` — use SDK `merge_contract_into_system_prompt` / `mergeContractIntoSystemPrompt` or place the appendix in a separate message.

Schema: [spec/turn-contract.schema.json](../../spec/turn-contract.schema.json) · Guide: [turn-contracts.md](../guides/turn-contracts.md).

## `POST /hybrid/complete`

Post-turn ingest + optional MSV reflect. When a turn contract is active for the session, also validates slots / advances the state machine.

**Request**

```json
{
  "bot_id": "uuid",
  "summary": "turn summary for episodic memory",
  "user_message": "original user message for reflect",
  "session_id": "optional-session-uuid",
  "reflect": true,
  "reflect_async": true,
  "filled_slots": { "check_in": "2026-09-01", "check_out": "2026-09-05" },
  "intent": "provide_dates",
  "assistant_text": "optional — scanned for reject_tokens only",
  "expected_version": 0,
  "idempotency_key": "uuid-per-logical-turn",
  "advance": true,
  "expected_step": "collect_dates"
}
```

Contract fields are optional. When `runtime_config.turn_contract` is set and `session_id` is present:

- `expected_version` is **required** (echo `contract_context.turn_version` from prepare).
- `idempotency_key` is recommended; SDKs auto-generate one in contract mode. Matching key after success returns the **cached** 200 body (no false 409 on retries).
- `filled_slots` uses null-delete semantics (`"slot": null` removes the key). Max payload 64 KiB, depth 3, 50 keys (enforced in request validation and resolver).
- Hard violations do **not** ingest or advance.
- Session turn state lives in `turn_sessions` (created on prepare). TTL matches `MEMORY_SESSION_TTL_SECONDS` (lazy expire + `POST /memory/purge-expired`).

**Response**

- **200** — sync reflect: `{ "status": "success", "ingested": true, "reflect": "completed", "current_msv": { ... }, "turn": { ... } }`
- **202** — async reflect: `{ "status": "accepted", "ingested": true, "reflect": "async", "bot_id": "uuid", "turn": { ... } }`
- **200** — `reflect: false`: `{ "status": "success", "ingested": true, "reflect": "skipped", "turn": { ... } }`

`turn` (when contract active): `{ "step", "slots", "advanced", "turn_version" }`.

**Contract errors** (`application/problem+json`)

| HTTP | Code | Host action |
|------|------|-------------|
| 422 | `TURN_CONTRACT_VIOLATION` | Use `remedial_prompt_hint` / `invalid_slots` / `missing_slots`; re-prompt |
| 422 | `TURN_REJECT_TOKEN` | Rewrite assistant text without reject tokens |
| 422 | `TURN_STEP_MISMATCH` | Align `expected_step` with prepare |
| 409 | `TURN_STATE_STALE` | Re-`prepare`; retry with fresh version + **new** idempotency key |
| 404 | `TURN_SESSION_EXPIRED` | Reset local flow; `prepare` to recreate session at step 0 |


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

Common codes: `BOT_NOT_FOUND`, `ACCESS_DENIED`, `INFERENCE_DOWN`, `MEMORY_DIM_MISMATCH`, `SOUL_INVALID`, `READY_DEGRADED`, `TURN_CONTRACT_VIOLATION`, `TURN_STEP_MISMATCH`, `TURN_STATE_STALE`, `TURN_SESSION_EXPIRED`, `TURN_REJECT_TOKEN`.

OpenAPI: `/openapi.json` · committed artifact: [openapi.kernel.json](openapi.kernel.json)

## Observability (OpenTelemetry)

Hybrid prepare/complete emit OpenTelemetry **spans** and a **`soulos.hybrid.duration`** histogram when `OTEL_EXPORTER_OTLP_ENDPOINT` or `SOULOS_OTEL_ENABLED=1` is set. Install optional extras: `pip install 'soulos-core[otel]'`. Compatible with Langfuse, Phoenix, Datadog OTLP ingest. Full guide: [observability.md](../guides/observability.md). Studio turn inspector exports prepare JSON/curl for local debugging only.

## `POST /state/reflect` (legacy)

Still supported. Prefer `hybrid/complete` with `reflect_async: true`.

**Request:** `{ "bot_id", "message", "reflect_async": false }`

## Client libraries

| Language | Class | Testing |
|----------|--------|---------|
| Python | `SoulHybridClient` from `soulos` — includes `run_turn()` | Covered in CI (`packages/soulos-sdk/python/tests/`) |
| TypeScript | `SoulHybridClient` from `@soulos/sdk` — includes `runTurn()` | Covered in CI (`packages/soulos-sdk/ts/tests/`, vitest) |
