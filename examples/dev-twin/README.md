# Dev Twin Example

Developer-assistant avatar — ingest repo context as episodic memory.

**Prerequisites:** kernel on `http://localhost:8000` — `docker compose up --build` ([Quickstart](../../docs/getting-started/quickstart.md)).

```bash
curl -X POST http://localhost:8000/v1/avatars -d @dev-twin.soul.json
curl -X POST http://localhost:8000/memory/ingest \
  -d '{"bot_id":"<id>","content":"SoulOS uses POST /v1/avatars to register avatars with HEXACO MSV."}'
```

Clone any GitHub repo and ingest README sections as episodic memories for RAG.

**See also:** [MCP workflow](../mcp/README.md) · [API reference](../../docs/reference/api.md)
