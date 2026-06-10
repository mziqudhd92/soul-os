# MCP workflow (5 minutes)

Connect Cursor to SoulOS and run ingest → retrieve against a live avatar.

## Prerequisites

```bash
docker compose up --build
# Kernel: http://localhost:8000
# Studio: http://localhost:8765 (optional)
```

Pull Ollama models if needed (`llama3`, `nomic-embed-text`).

## 1. Get a `bot_id`

**Option A — Studio:** Open http://localhost:8765 → build soul → **Deploy to kernel** → copy avatar id.

**Option B — curl:**

```bash
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/support-bot/support-bot.soul.json
```

## 2. Configure Cursor MCP

Copy [cursor-mcp.json](cursor-mcp.json) into Cursor MCP settings (remote URL):

```text
http://localhost:8000/mcp/sse
```

## 3. Ingest memory

In Cursor chat (with SoulOS MCP enabled):

> Use SoulOS `ingest_memory` for bot `<your-bot-id>`: "Full refunds within 30 days of purchase."

## 4. Retrieve memory

> Use SoulOS `retrieve_memory` for the same bot with query "refund policy" and tell me what you find.

## 5. Optional — identity

> Call `get_identity` for my bot and summarize the HEXACO baseline.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP connection failed | Kernel running on :8000? |
| Ingest/retrieve errors | Ollama up? `curl http://localhost:11434/api/tags` |
| 403 on tools | Cloud mode — use gateway + API key |

**Docs:** [MCP guide](../../docs/guides/mcp.md) · [MCP tools reference](../../docs/reference/mcp-tools.md) · [docs hub](../../docs/README.md)
