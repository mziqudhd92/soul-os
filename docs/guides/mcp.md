# MCP Integration Guide

SoulOS exposes a Model Context Protocol server on the **kernel** so Cursor, Claude Desktop, and other MCP hosts can use avatar memory, identity, and MSV as **composable tools** — without custom integration code.

## MCP vs SDK vs Studio

| Use | Best choice |
|-----|-------------|
| IDE agent (Cursor) maintaining FAQ / memory | **MCP** |
| Your app or website chat widget | **@soulos/sdk** or REST |
| Hand-tuning `.soul.json` | **Soul Studio** |

MCP does not replace the SDK. It complements it for **agent hosts** that already speak MCP.

## Endpoint (HTTP SSE)

```text
http://localhost:8000/mcp/sse
```

With `docker compose up`, the kernel listens on port **8000**. MCP uses the same Postgres + embedder stack as REST — if Ollama/embeddings are down, `ingest_memory` and `retrieve_memory` will fail.

## Tools

| Tool | Purpose |
|------|---------|
| `ingest_memory` | Store episodic memory (`bot_id`, `content`) |
| `retrieve_memory` | Semantic recall (`bot_id`, `query`, optional `top_k`) |
| `get_identity` | Persona + `baseline_msv` / `current_msv` JSON |
| `register_avatar` | Create avatar from full `.soul.json` object |
| `list_avatars` | List avatars (tenant-scoped when auth enabled) |
| `update_cognitive_state` | Force-update MSV (`bot_id`, `new_msv`) |

Tool JSON schemas: [reference/mcp-tools.md](../reference/mcp-tools.md).

**Not exposed via MCP:** `chat/generate` and `msv_update` streaming — use REST/SDK for dual-process chat.

## Resources

| URI | Content |
|-----|---------|
| `memory://episodic/{bot_id}` | Recent episodic memory log |
| `soul://identity/{bot_id}` | Identity + MSV as JSON |

## Prompts

| Name | Args | Returns |
|------|------|---------|
| `identity` | `bot_id` | Persona + current MSV text (same as `get_identity` formatter) |

## Cursor configuration

See [examples/mcp/cursor-mcp.json](../../examples/mcp/cursor-mcp.json). In Cursor Settings → MCP, add a **remote** server:

```json
{
  "mcpServers": {
    "soulos": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

## Hosted API (SoulOS Cloud / gateway)

```text
https://<your-gateway-host>/mcp/sse
Authorization: Bearer <SOULOS_API_KEY>
```

The gateway proxies MCP SSE with the same Bearer key as REST. Do not expose the kernel port publicly without `REQUIRE_AUTH=1`.

## Example workflow

1. Register avatar: Studio **Deploy**, `POST /v1/avatars`, or MCP `register_avatar`
2. In Cursor: *"Ingest into SoulOS that refunds are allowed within 30 days"* → `ingest_memory`
3. *"What is the refund policy?"* → `retrieve_memory` then answer
4. Your app uses `@soulos/sdk` `sendMessage` — RAG retrieves the same memories

Walkthrough: [examples/mcp/README.md](../../examples/mcp/README.md).

## Implementation

Kernel MCP server: [packages/soulos-core/mcp_server.py](../../packages/soulos-core/mcp_server.py).

**See also:** [MCP tools reference](../reference/mcp-tools.md) · [API reference](../reference/api.md) · [Soul Builder](../getting-started/soul-builder.md) · [SECURITY.md](../../SECURITY.md)
