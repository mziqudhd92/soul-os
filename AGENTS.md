# SoulOS — agent instructions

Instructions for AI coding agents (Cursor, Claude Code, Copilot, etc.) working in this repository.

## Project identity

- **SoulOS** — open-source avatar runtime (NOT Next.js; legacy Next app was removed).
- **Repo:** https://github.com/mziqudhd92/soul-os
- **Read first:** `docs/SOULOS_AGENT_CONTEXT.md` or root `llms.txt` / `llms-full.txt`

## Stack

| Component | Path | Port |
|-----------|------|------|
| Kernel | `packages/soulos-core/` | 8000 |
| Gateway | `packages/soulos-gateway/` | 8080 |
| Soul Studio | `packages/soulos-studio/` | 8765 |
| TS SDK | `packages/soulos-sdk/ts/` | — |
| Python SDK | `packages/soulos-sdk/python/` | — |

Boot: `docker compose up --build` from repo root. Tests: `npm run test:all`.

## Conventions

- Soul files: `spec/soul.schema.json` — HEXACO keys H,E,X,A,C,O in range -1..1.
- MCP server: `packages/soulos-core/mcp_server.py`, HTTP SSE at `/mcp/sse`.
- Runtime pipeline: `packages/soulos-core/runtime/` (embedder, memory, pipeline, reflector).
- Do not reintroduce Node/React for Studio — Python FastAPI + static HTML/CSS/JS only.
- Minimize diff scope; match existing naming (`soulos-*`, SoulOS not SentiCore in user-facing text).

## Security

- Never commit `.env`, `keys.json`, or real API keys.
- `REQUIRE_AUTH=0` is local dev only; document gateway auth for production.
- Demo keys (`sk_test_demo_key_for_local_dev`) are for local cloud compose only.

## Docs maintenance

When changing APIs, MCP tools, or ports, update: `docs/reference/api.md`, `docs/reference/mcp-tools.md`, `docs/SOULOS_AGENT_CONTEXT.md`, and `llms.txt` links if paths change.
