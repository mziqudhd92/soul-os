# soulos-core (kernel)

FastAPI **SoulOS kernel** — personality (HEXACO MSV), hybrid episodic memory (pgvector + FTS), dual-process routing, Phase B shared conversation memory / handoffs, REST + MCP.

- **Run (Docker):** `docker compose up soulos-kernel` from repo root
- **Run (local):** `uvicorn main:app --host 0.0.0.0 --port 8000` (needs Postgres + inference)
- **MCP:** `http://localhost:8000/mcp/sse`
- **Tests:** `pytest` or `npm run test:kernel` / `npm run test:eval` from repo root

Key runtime modules (0.6+): `memory.py` / `memory_rank.py`, `msv_update.py`, `trait_directives.py`, `dual_process.py`, `conversation_memory.py`, `memory_consolidate.py`, `capability_query.py`.

Docs: [API reference](../../docs/reference/api.md) · [MCP tools](../../docs/reference/mcp-tools.md) · [0.6.0 report](../../docs/reports/phase-b-ml-improvements.md)
