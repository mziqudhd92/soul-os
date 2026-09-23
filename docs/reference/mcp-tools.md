# MCP tools reference

SoulOS kernel MCP server name: `soulos-kernel`.

Transport: HTTP SSE at `/mcp/sse` (see [MCP guide](../guides/mcp.md)). Self-host: `http://localhost:8000/mcp/sse`. Cloud: gateway URL with Bearer API key.

**Not exposed via MCP:** `chat/generate` streaming — use REST or `@soulos/sdk`.

All tool responses are JSON strings in `TextContent`. Errors use the same shape as REST Problem Details: `{"error": true, "code", "status", "detail"}` (including validation failures and `SoulOSProblem` from hybrid/tenant checks).

## `ingest_memory`

Store text in episodic memory (pgvector embedding).

| Argument | Type | Required |
|----------|------|----------|
| `bot_id` | string | yes |
| `content` | string | yes |
| `session_id` | string | no |

Response: `{"status": "success", "bot_id": "...", "message": "Memory ingested"}`

## `retrieve_memory`

Semantic similarity search over episodic memory.

| Argument | Type | Required | Default |
|----------|------|----------|---------|
| `bot_id` | string | yes | — |
| `query` | string | yes | — |
| `top_k` | integer | no | 5 |
| `session_id` | string | no | — |

Response: `{"bot_id": "...", "query": "...", "memories": ["...", ...]}`

## `forget_memory`

Delete episodic memories whose content contains `content_match` (case-insensitive; `%` / `_` are escaped).

| Argument | Type | Required |
|----------|------|----------|
| `bot_id` | string | yes |
| `content_match` | string | yes |

Response: `{"status": "success", "bot_id": "...", "deleted": N}`

## `delete_session`

Delete session-scoped memories and turn-contract session state (same as `DELETE /memory/session/{bot_id}/{session_id}`).

| Argument | Type | Required |
|----------|------|----------|
| `bot_id` | string | yes |
| `session_id` | string | yes |

Response: `{"status": "success", "deleted": N, "turn_sessions_deleted": N, "bot_id", "session_id"}`

## `ensure_avatar`

Idempotent avatar bootstrap by `external_key` (same as `POST /v1/avatars/ensure`).

| Argument | Type | Required |
|----------|------|----------|
| `external_key` | string | yes |
| `soul` | object or JSON string | yes |
| `runtime_config` | object | no |

## `hybrid_prepare`

Hybrid sidecar step 1 — same as `POST /hybrid/prepare`.

| Argument | Type | Required | Default |
|----------|------|----------|---------|
| `bot_id` | string | yes | — |
| `query` | string | yes | — |
| `session_id` | string | no | — |
| `top_k` | integer | no | 5 |

## `hybrid_complete`

Hybrid sidecar step 2 — same as `POST /hybrid/complete` (supports turn-contract fields).

| Argument | Type | Required | Default |
|----------|------|----------|---------|
| `bot_id` | string | yes | — |
| `summary` | string | yes | — |
| `user_message` | string | no | — |
| `session_id` | string | no | — |
| `reflect` | boolean | no | true |
| `reflect_async` | boolean | no | false |
| `filled_slots` / `intent` / `assistant_text` / `expected_version` / `expected_step` / `idempotency_key` / `advance` | — | no | turn-contract fields |

## `get_identity`

| Argument | Type | Required |
|----------|------|----------|
| `bot_id` | string | yes |

Response: `{"bot_id", "name", "role", "description", "baseline_msv", "current_msv"}`

## `register_avatar`

| Argument | Type | Required |
|----------|------|----------|
| `soul` | object | yes — full [soul file](../reference/soul-standard.md) |

Response: `{"id", "name", "role", "attachment_style", "baseline_msv", "current_msv"}`

## `list_avatars`

| Argument | Type | Required | Default |
|----------|------|----------|---------|
| `limit` | integer | no | 50 (max 50) |

Response: `{"avatars": [{"id", "name", "role", "status"}, ...]}`

Tenant-scoped when `REQUIRE_AUTH=1`.

## `update_cognitive_state`

| Argument | Type | Required |
|----------|------|----------|
| `bot_id` | string | yes |
| `new_msv` | object or JSON string | yes |

Response: `{"status": "success", "bot_id": "...", "message": "..."}`
