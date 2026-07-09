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

## Testing (TDD)

Write or update tests **before or alongside** behavior changes — CI blocks merges on failing tests.

| Command | Scope |
|---------|--------|
| `npm run test:all` | Kernel, bridge, gateway, studio, Python SDK |
| `npm run test:kernel` | `packages/soulos-core/test_*.py` |
| `npm run test:sdk` | `packages/soulos-sdk/python/tests/` |
| `npm run doc:check` | Hybrid doc drift + OpenAPI contract |

**Conventions**

- Kernel HTTP tests: `httpx.AsyncClient` + `ASGITransport(app=app)` with dependency overrides (`test_main.py` mocks).
- Pure logic: unit tests without HTTP (e.g. `test_persona_simple.py`, `runtime/` helpers).
- SDK: mock `httpx` / `_request`; assert RFC 7807 `SoulOSError` codes.
- New API routes need route tests + unit tests for service functions when non-trivial.
- Persona / hybrid regressions: extend `test_persona_simple.py` or run `python3 scripts/soulos-eval.py`.

Do not merge untested public API or SDK surface changes.

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

## Git commits (agents)

Agent-created commits must use **`fcursor <fcursor@iwantmoneyfromcursor.com>`** — not `cursoragent@cursor.com`. Set `GIT_AUTHOR_*` and `GIT_COMMITTER_*` env vars per commit; do not change `git config`.
