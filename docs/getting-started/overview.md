# Getting started with SoulOS

SoulOS is an open-source runtime for persistent AI avatars — HEXACO psychometrics, episodic memory, and dual-process inference. This page orients you to the stack; follow the linked guides for hands-on steps.

**Docs index:** [docs/README.md](../README.md)

## Fast paths

| Goal | Time | Start here |
|------|------|------------|
| Kernel smoke test (curl) | 5 min | [Quickstart — Path A](quickstart.md#path-a) |
| MCP in Cursor | 5 min | [examples/mcp](../../examples/mcp/README.md) |
| Support bot + dev twin | 15 min | [Quickstart](quickstart.md) |
| Tune `.soul.json` in browser | 10 min | [Soul Builder](soul-builder.md) |

## Prerequisites

- **Docker & Docker Compose** — kernel, Postgres, optional Ollama (`docker compose up --build`)
- **Ollama** (recommended locally) — `llama3` and `nomic-embed-text`, or a remote OpenAI-compatible endpoint via `INFERENCE_API_URL`
- **Python 3.12+** — optional; `pip install soulos-studio` and the Python SDK
- **Node.js 20+** — optional; `npm run up`, `npm run test:all`, SDK build

## Stack at a glance

| Component | Port / transport | Role |
|-----------|------------------|------|
| **SoulOS kernel** | `http://localhost:8000` | Personality, memory, dual-process chat, REST + MCP |
| **MCP (HTTP SSE)** | `http://localhost:8000/mcp/sse` | Cursor / Claude tool integration — [MCP guide](../guides/mcp.md) |
| **Soul Studio** | `http://localhost:8765` | Soul Builder UI — [Soul Builder](soul-builder.md) |
| **@soulos/sdk** | HTTP to kernel or gateway | App integrations — [Python bot](../guides/python-bot.md), [Quickstart](quickstart.md) |

Architecture detail: [reference/architecture.md](../reference/architecture.md).

## Boot the cluster

From the repo root:

```bash
docker compose up --build
# Kernel: http://localhost:8000
# Studio:  http://localhost:8765
```

Full curl walkthrough: [Quickstart](quickstart.md).

## Register an avatar

POST a `.soul.json` file (validated against [spec/soul.schema.json](../../spec/soul.schema.json)):

```bash
curl -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/support-bot/support-bot.soul.json
```

The response `id` is your `bot_id` for chat, memory, and MCP tools. Invalid traits return `422` with a readable error list.

## Connect MCP (Cursor / Claude)

SoulOS exposes MCP on the **kernel** over HTTP SSE — not a separate stdio process.

```text
http://localhost:8000/mcp/sse
```

Configuration, tool list, and a 5-minute workflow: [MCP guide](../guides/mcp.md) · [examples/mcp](../../examples/mcp/README.md) · [MCP tools reference](../reference/mcp-tools.md).

## Security (local dev)

Default self-host mode uses `REQUIRE_AUTH=0` — fine for solo local use only. Do not expose port **8000** (or MCP `/mcp/*`) on public networks without gateway auth. See [SECURITY.md](../../SECURITY.md) and [Self-hosted deployment](../deployment/self-hosted.md).

## Next steps

- [Soul standard](../reference/soul-standard.md) — `.soul.json` anatomy
- [API reference](../reference/api.md) — REST + SSE events
- [Psychometrics cheat sheet](../guides/psychometrics.md) — what HEXACO sliders do
- [Deployment overview](../deployment/README.md) — self-host vs Cloud
