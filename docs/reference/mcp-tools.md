# MCP tools reference

SoulOS kernel MCP server name: `soulos-kernel`.

Transport: HTTP SSE at `/mcp/sse` (see [MCP guide](../guides/mcp.md)). Self-host: `http://localhost:8000/mcp/sse`. Cloud: gateway URL with Bearer API key.

**Not exposed via MCP:** `chat/generate` and `msv_update` streaming — use REST or `@soulos/sdk`.

All tool responses are JSON strings in `TextContent`.

## `ingest_memory`

Store text in episodic memory (pgvector embedding).

| Argument | Type | Required |
|----------|------|----------|
| `bot_id` | string | yes |
| `content` | string | yes |

Response: `{"status": "success", "bot_id": "...", "message": "Memory ingested"}`

## `retrieve_memory`

Semantic similarity search over episodic memory.

| Argument | Type | Required | Default |
|----------|------|----------|---------|
| `bot_id` | string | yes | — |
| `query` | string | yes | — |
| `top_k` | integer | no | 5 |

Response: `{"bot_id": "...", "query": "...", "memories": ["...", ...]}`

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
