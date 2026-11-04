# MCP Integration Guide

SoulOS exposes a Model Context Protocol server on the **kernel** so Cursor, Claude Desktop, and other MCP hosts can use avatar memory, identity, and MSV as **composable tools** — without custom integration code.

## MCP vs SDK vs Studio

| Use | Best choice |
|-----|-------------|
| IDE agent (Cursor) maintaining FAQ / memory | **MCP** |
| Your app or website chat widget | **@soulos/sdk** or REST |
| Hand-tuning `.soul.json` | **Soul Studio** |

MCP does not replace the SDK. It complements it for **agent hosts** that already speak MCP.

## Endpoints

| Transport | URL |
|-----------|-----|
| HTTP SSE (Cursor-compatible) | `http://localhost:8000/mcp/sse` |
| Streamable HTTP | `http://localhost:8000/mcp` (POST/GET/DELETE) |

With `docker compose up`, the kernel listens on port **8000**. Prefer Streamable HTTP when the host supports it; keep SSE as fallback.

MCP uses the same Postgres + embedder stack as REST — if Ollama/embeddings are down, `ingest_memory` and `retrieve_memory` will fail.

## Tools (summary)

| Tool | Purpose |
|------|---------|
| `ingest_memory` / `retrieve_memory` | Episodic store + semantic recall (novelty gating on ingest) |
| `ingest_conversation_memory` / `retrieve_conversation_memory` | Shared conversation memory |
| `create_handoff` | Structured handoff (allowlisted targets) |
| `consolidate_memory` | Semantic compression (no-op if too early; rate-limited) |
| `hybrid_prepare` / `hybrid_complete` | Sidecar turn; complete is the **commit** |
| `apply_msv_delta` | Semantic HEXACO shifts (`appraisal_reasoning` required) |
| `reflect_cognitive_state` | System 2 reflect (rate-limited; appraisal required) |
| `get_identity` / `register_avatar` / `list_avatars` / `ensure_avatar` | Identity lifecycle |
| `update_cognitive_state` | **Admin only** (`SOULOS_MCP_ADMIN_TOOLS=1`, or API-key `scopes: ["mcp:admin:msv_write"]` via gateway → `X-SoulOS-Scopes`) |

Full schemas: [reference/mcp-tools.md](../reference/mcp-tools.md).

**Not exposed via MCP:** `chat/generate` streaming — use REST/SDK.

## Resources

| URI | Content |
|-----|---------|
| `memory://episodic/{bot_id}` | Recent episodic log (default 50; `?limit=`) |
| `soul://identity/{bot_id}` | Identity + MSV |
| `session://turn/{bot_id}/{session_id}` | Turn session JSON |
| `soul://schema` | Soul JSON schema |
| `msv://drift/{bot_id}` | Baseline/current/delta + `behavioral_summary` |

## Prompts

| Name | Behavior |
|------|----------|
| `identity` | Persona + MSV text |
| `hybrid_turn` | Server-side prepare; host generates reply then `hybrid_complete` |
| `soul_author` | Guide `.soul.json` drafting |
| `debug_msv` | Drift + safe mutation guidance |

## Cursor configuration

```json
{
  "mcpServers": {
    "soulos": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

Streamable HTTP hosts may use `http://localhost:8000/mcp`.

## Hosted API (gateway)

```text
https://<your-gateway-host>/mcp/sse
Authorization: Bearer <SOULOS_API_KEY>
```

Gateway proxies `/mcp` and `/mcp/*` with Bearer keys, preserves `Mcp-Session-Id`, and caps concurrent MCP streams per key. It injects `X-SoulOS-Account-Id` / `X-SoulOS-Gateway-Secret` / optional `X-SoulOS-Scopes` from the key record — clients cannot forge those headers. Do not expose the kernel port publicly without `REQUIRE_AUTH=1`.

Admin MSV force-write: put `"scopes": ["mcp:admin:msv_write"]` on the API key (see [cloud deployment](../deployment/cloud.md) and [gateway headers](gateway-headers.md)).

## Outbound MCP (kernel as client)

Optional: enable `SOULOS_MCP_CLIENT=1` and configure `SOULOS_MCP_SERVERS_JSON` so hybrid/reflect can call external allowlisted tools. Pins (`schema_sha256`), SSRF blocks, and untrusted output wraps apply — details in [mcp-tools.md](../reference/mcp-tools.md#outbound-mcp-client-kernel--external-tools).

## Security notes

See [SECURITY.md](../../SECURITY.md): tenant-scoped `SecurityContext`, admin-gated force MSV (scopes or `SOULOS_MCP_ADMIN_TOOLS`), handoff allowlists, session-principal binding, outbound SSRF / schema-pin controls.

## Implementation

Kernel: [packages/soulos-core/mcp_server.py](../../packages/soulos-core/mcp_server.py) · runtime services under `packages/soulos-core/runtime/` (`mcp_client`, `security_context`, `memory_trust`, …).

**See also:** [MCP tools reference](../reference/mcp-tools.md) · [Gateway headers](gateway-headers.md) · [API reference](../reference/api.md) · [SECURITY.md](../../SECURITY.md)
