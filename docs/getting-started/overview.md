# Getting started with SoulOS

SoulOS is an open-source runtime for persistent AI avatars — HEXACO psychometrics, episodic memory, and dual-process inference. This page orients you to the stack; follow the linked guides for hands-on steps.

**Docs index:** [docs/README.md](../README.md)

## Fast paths

| Goal | Time | Start here |
|------|------|------------|
| **Sidecar hybrid (existing LLM app)** | 15 min | [My first sidecar](../tutorials/my-first-sidecar.md) · [Quickstart Path C](quickstart.md#path-c) |
| Kernel smoke test (curl) | 5 min | [Quickstart — Path A](quickstart.md#path-a) |
| MCP in Cursor | 5 min | [examples/mcp](../../examples/mcp/README.md) |
| Support bot + dev twin | 15 min | [Quickstart](quickstart.md) |
| Tune `.soul.json` in browser | 10 min | [Soul Builder](soul-builder.md) |

**Ports:** full stack kernel **`:8000`** (`docker compose up`); sidecar stack kernel **`:8001`** (`docker-compose.sidecar.yml`).

## Prerequisites

- **Docker & Docker Compose** — kernel, Postgres, optional Ollama (`docker compose up --build`)
- **Inference** — Ollama (`llama3`, `nomic-embed-text`) or [inference bridge](deployment/inference.md) for AWS/GCP; set `INFERENCE_API_URL` accordingly
- **Python 3.12+** — optional; `pip install soulos-studio` and the Python SDK
- **Node.js 20+** — optional; `npm run up`, `npm run test:all`, SDK build

## Stack at a glance

| Component | Port / transport | Role |
|-----------|------------------|------|
| **SoulOS kernel** | `http://localhost:8000` (full) / `:8001` (sidecar) | Personality, memory, hybrid + dual-process chat, REST + MCP |
| **MCP (HTTP SSE)** | `http://localhost:8000/mcp/sse` | Cursor / Claude tool integration — [MCP guide](../guides/mcp.md) |
| **Soul Studio** | `http://localhost:8765` | Soul Builder UI — [Soul Builder](soul-builder.md) |
| **@soulos/sdk** | HTTP to kernel or gateway | App integrations — [sidecar](../guides/sidecar-integration.md), [Python bot](../guides/python-bot.md) |

Architecture detail: [reference/architecture.md](../reference/architecture.md).

## Boot the cluster

From the repo root:

```bash
docker compose up --build
# Kernel: http://localhost:8000
# Studio:  http://localhost:8765
```

Sidecar (your LLM keeps generation):

```bash
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up --build
# Kernel: http://localhost:8001
```

Full curl walkthrough: [Quickstart](quickstart.md).

## Register an avatar

POST a `.soul.json` file (validated against [spec/soul.schema.json](../../spec/soul.schema.json)):

```bash
curl -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/support-bot/support-bot.soul.json
```

Prefer idempotent `POST /v1/avatars/ensure` with `external_key` for apps — [identity model](../guides/identity-model.md).

The response `id` is your `bot_id` for chat, memory, and MCP tools. Invalid traits return `422` with RFC 7807 `code: SOUL_INVALID`.

## Connect MCP (Cursor / Claude)

SoulOS exposes MCP on the **kernel** over HTTP SSE — not a separate stdio process.

```text
http://localhost:8000/mcp/sse
```

Configuration, tool list, and a 5-minute workflow: [MCP guide](../guides/mcp.md) · [examples/mcp](../../examples/mcp/README.md) · [MCP tools reference](../reference/mcp-tools.md).

## Security (local dev)

Default self-host mode uses `REQUIRE_AUTH=0` — fine for solo local use only. Do not expose port **8000** (or MCP `/mcp/*`) on public networks without gateway auth. See [SECURITY.md](../../SECURITY.md) and [Self-hosted deployment](../deployment/self-hosted.md).

## Next steps

- [My first sidecar](../tutorials/my-first-sidecar.md) — hybrid primary path
- [Soul standard](../reference/soul-standard.md) — `.soul.json` anatomy
- [API reference](../reference/api.md) — REST + SSE events
- [Psychometrics cheat sheet](../guides/psychometrics.md) — what HEXACO sliders do
- [Deployment overview](../deployment/README.md) — self-host vs Cloud
