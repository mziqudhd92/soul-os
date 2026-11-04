# MCP tools reference

SoulOS kernel MCP server name: `soulos-kernel`.

Transport: HTTP SSE at `/mcp/sse` and Streamable HTTP at `/mcp` (see [MCP guide](../guides/mcp.md)). Self-host: `http://localhost:8000/mcp/sse`. Cloud: gateway URL with Bearer API key (`Mcp-Session-Id` preserved end-to-end).

**Not exposed via MCP:** `chat/generate` streaming — use REST or `@soulos/sdk`.

All tool responses are JSON strings in `TextContent`. Errors use Problem Details (`error`, `code`, `status`, `detail`) and set MCP `isError` when applicable.

### Admin scope

Admin force-write tool `update_cognitive_state` is omitted from `list_tools` unless:

- kernel `SOULOS_MCP_ADMIN_TOOLS=1`, or
- caller has scope `mcp:admin:msv_write` via `X-SoulOS-Scopes`

On SoulOS Cloud, set `"scopes": ["mcp:admin:msv_write"]` on the API key in `keys.json` / `SOULOS_API_KEYS`. The gateway injects `X-SoulOS-Scopes`; clients cannot forge it. Prefer `apply_msv_delta` / `reflect_cognitive_state` for normal MSV changes.

MCP episodic / conversation writes are stored wrapped as `<untrusted_memory trust_level="external_mcp">`.

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
| `mood_congruent` | boolean | no | false |
| `recency_weight` | number | no | 0 |

Response: `{"bot_id": "...", "query": "...", "memories": ["...", ...], "mood_congruent": ...}`

Uses the same hybrid ranking stack as REST (dense + FTS → RRF → MMR). When `mood_congruent` is true, results are re-ranked with the avatar's current MSV.

## `ingest_conversation_memory` / `retrieve_conversation_memory`

Shared conversation memory (MCP writes tagged `trust_level=external_mcp`).

`retrieve_conversation_memory` accepts the same optional ranking knobs as `retrieve_memory`:

| Argument | Type | Required | Default |
|----------|------|----------|---------|
| `conversation_id` | string | yes | — |
| `query` | string | yes | — |
| `top_k` | integer | no | 5 |
| `bot_id` | string | when `mood_congruent` | — |
| `mood_congruent` | boolean | no | false |
| `recency_weight` | number | no | 0 |

`mood_congruent=true` requires `bot_id` (loads that avatar's `current_msv` for rerank).

## `create_handoff`

Requires structured fields: `task_summary`, `unresolved_constraints`, `user_emotional_state`, `source_bot_stance`. Honors `runtime_config.allowed_handoff_targets`.

## `consolidate_memory`

Rate-limited. Returns `too_early` when below `CONSOLIDATE_MIN_CANDIDATES`.

## `apply_msv_delta`

Requires `appraisal_reasoning`, `trait` (`H|E|X|A|C|O`), `shift` (`slight_increase` | `moderate_increase` | `slight_decrease` | `moderate_decrease`).

## `reflect_cognitive_state`

Requires `appraisal_reasoning` + `message`. Per-tenant rate limit.

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

**Admin only** — see [Admin scope](#admin-scope) above. Hidden from `list_tools` without privilege.

| Argument | Type | Required |
|----------|------|----------|
| `bot_id` | string | yes |
| `new_msv` | object or JSON string | yes |

Response: `{"status": "success", "bot_id": "...", "message": "..."}`

## Resources & prompts

| Kind | Name / URI |
|------|------------|
| Resource | `memory://episodic/{bot_id}` · `soul://identity/{bot_id}` · `session://turn/{bot_id}/{session_id}` · `soul://schema` · `msv://drift/{bot_id}` |
| Prompt | `identity` · `hybrid_turn` · `soul_author` · `debug_msv` |

## Outbound MCP client (kernel → external tools)

When `SOULOS_MCP_CLIENT=1` and `SOULOS_MCP_SERVERS_JSON` lists servers, hybrid/reflect can call allowlisted remote tools (`server__tool` names). Controls:

| Control | Behavior |
|---------|----------|
| SSRF | DNS resolve then block private/link-local (unless `SOULOS_MCP_ALLOW_PRIVATE_NET=1`); `follow_redirects=False` |
| Allowlist | Per-server `allow_tools`; optional soul `allowed_mcp_servers` |
| Schema pin | Optional `schema_sha256` on each allow-tool — re-fetches `tools/list` and rejects pin mismatch before `tools/call` |
| Output | Truncated + wrapped as `<untrusted_tool_output>`; arg exfil heuristics block secrets / soul dumps |
| Budget | `SOULOS_MCP_MAX_TOOL_ITERATIONS` (default 3) |

Example `SOULOS_MCP_SERVERS_JSON`:

```json
{
  "servers": [
    {
      "name": "ext",
      "url": "https://tools.example.com/mcp",
      "auth_env_key": "EXT_MCP_TOKEN",
      "allow_tools": [
        {
          "name": "search",
          "description_override": "Safe search",
          "schema_sha256": "<sha256 of tools/list entry JSON>"
        }
      ]
    }
  ]
}
```

See [SECURITY.md](../../SECURITY.md) and [MCP guide](../guides/mcp.md).
