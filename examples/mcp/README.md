# MCP workflow (~10 minutes)

Connect **Cursor** to SoulOS and run ingest → retrieve against a live avatar.

**Prerequisite tutorial:** [Python bot](../docs/guides/python-bot.md) or [Quickstart Path A](../docs/getting-started/quickstart.md#path-a) — you need a running kernel and a `bot_id`.

## What you will learn

- Configure Cursor MCP over HTTP SSE (not stdio)
- Use `ingest_memory` and `retrieve_memory` from the IDE
- Share the same avatar between Cursor tools and your app SDK

## Prerequisites

```bash
docker compose up --build
# Kernel: http://localhost:8000
```

Pull Ollama models if needed: `llama3`, `nomic-embed-text`.

```bash
curl -s http://localhost:11434/api/tags
```

---

## 1. Get a `bot_id`

**Option A — Studio:** http://localhost:8765 → build soul → **Deploy to kernel** → copy avatar id.

**Option B — curl:**

```bash
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/support-bot/support-bot.soul.json | python3 -m json.tool
```

Save the `id` field — example: `export BOT_ID=...`

---

## 2. Configure Cursor MCP

In Cursor **Settings → MCP**, add a remote server (or merge [cursor-mcp.json](cursor-mcp.json)):

```json
{
  "mcpServers": {
    "soulos": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

Restart or reload MCP if Cursor does not connect immediately.

**Verify:** MCP tools list should include `ingest_memory`, `retrieve_memory`, `get_identity`, etc.

---

## 3. Ingest memory

In Cursor chat (SoulOS MCP enabled):

> Use SoulOS `ingest_memory` for bot `<your-bot-id>` with content: "Full refunds within 30 days of purchase."

**Expected:** tool returns success JSON.

---

## 4. Retrieve memory

> Use SoulOS `retrieve_memory` for the same bot with query "refund policy" and summarize what you find.

**Expected:** memories array contains your ingested line.

---

## 5. Optional — identity

> Call `get_identity` for my bot and summarize the HEXACO baseline.

Useful before tuning sliders in Studio — compare `baseline_msv` vs `current_msv` after long chats.

---

## What MCP does *not* do

Chat streaming (`POST /chat/generate`) is **not** on MCP — use REST or `@soulos/sdk` / Python SDK for user-facing chat. MCP is for **agent tooling** (memory, identity, registration).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP connection failed | Kernel on :8000? `curl http://localhost:8000/health` |
| Ingest/retrieve errors | Ollama up? embeddings need `nomic-embed-text` |
| 403 on tools | Cloud mode — gateway URL + Bearer API key |
| Wrong bot data | Confirm `bot_id` matches deployed avatar |

---

**Docs:** [MCP guide](../../docs/guides/mcp.md) · [MCP tools](../../docs/reference/mcp-tools.md) · [Tutorials hub](../../docs/tutorials/README.md)
