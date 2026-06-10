# soulos-core (kernel)

FastAPI **SoulOS kernel** — personality (HEXACO MSV), episodic memory (pgvector), dual-process inference, REST + MCP.

- **Run (Docker):** `docker compose up soulos-kernel` from repo root
- **Run (local):** `uvicorn main:app --host 0.0.0.0 --port 8000` (needs Postgres + inference)
- **MCP:** `http://localhost:8000/mcp/sse`
- **Tests:** `pytest` or `npm run test:kernel` from repo root

Key modules: `main.py`, `mcp_server.py`, `runtime/` (embedder, memory, pipeline, reflector).

Docs: [API reference](../../docs/reference/api.md) · [MCP tools](../../docs/reference/mcp-tools.md)
