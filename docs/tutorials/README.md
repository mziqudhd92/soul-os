# Tutorials — start here

**Recommended first tutorial:** **[My first sidecar](my-first-sidecar.md)** — wire SoulOS beside an existing LLM call in ~15 minutes.

Same list appears online at **https://mziqudhd92.github.io/soul-os/** or in **Soul Studio** → **Tutorials** at http://localhost:8765.

## Learning path (recommended order)

| # | Time | Tutorial | You will learn |
|---|------|----------|----------------|
| **1** | 15 min | **[My first sidecar](my-first-sidecar.md)** | `ensure → prepare → your LLM → complete` + memory on turn 2 |
| 2 | 25 min | [Python bot integration](../guides/python-bot.md) | Full-chat: soul + memory + `send_message` |
| 3 | 10 min | [Kernel smoke test (curl)](../getting-started/quickstart.md#path-a) | Register soul, ingest memory, SSE chat without code |
| 4 | 15 min | [Build your first soul (Wizard)](../../packages/soulos-studio/soulos_studio/content/tutorials/first-soul-wizard.md) | Create `.soul.json` in Studio without hand-editing JSON |
| 5 | 12 min | [Deploy and test chat](../../packages/soulos-studio/soulos_studio/content/tutorials/deploy-and-chat.md) | Deploy from Studio, watch HEXACO drift live |
| 6 | 15 min | [Support bot + dev twin](../getting-started/quickstart.md) | Two avatars, same kernel — only soul + memory differ |
| 7 | 10 min | [MCP in Cursor](../../examples/mcp/README.md) | IDE tools for memory and identity |
| 8 | 15 min | [MCP deep dive](../guides/mcp.md) | Full MCP tool surface and gateway auth |

## All tutorials by topic

### Integrations (start here)

| Tutorial | File |
|----------|------|
| **My first sidecar** (recommended first) | [my-first-sidecar.md](my-first-sidecar.md) |
| Python bot (full-chat) | [python-bot.md](../guides/python-bot.md) |
| Session memory / GDPR | [session-memory.md](../guides/session-memory.md) |
| Migrate from system prompt | [migrate-from-system-prompt.md](../guides/migrate-from-system-prompt.md) |
| Troubleshooting | [troubleshooting.md](../guides/troubleshooting.md) |
| MCP (Cursor / Claude) | [mcp.md](../guides/mcp.md) |
| HEXACO sliders | [psychometrics.md](../guides/psychometrics.md) |

### Studio (browser UI)

| Tutorial | File |
|----------|------|
| Build your first soul | [first-soul-wizard.md](../../packages/soulos-studio/soulos_studio/content/tutorials/first-soul-wizard.md) |
| Deploy and test chat | [deploy-and-chat.md](../../packages/soulos-studio/soulos_studio/content/tutorials/deploy-and-chat.md) |
| Soul Builder guide | [soul-builder.md](../getting-started/soul-builder.md) |

`docker compose up` → http://localhost:8765 — or `pip install -e packages/soulos-studio && soulos-studio`

### Kernel & API

| Tutorial | File |
|----------|------|
| 15-minute quickstart | [quickstart.md](../getting-started/quickstart.md) |
| API & SSE | [api.md](../reference/api.md) |
| Soul file anatomy | [soul-standard.md](../reference/soul-standard.md) |

### Deployment

| Tutorial | File |
|----------|------|
| Self-hosted Docker | [self-hosted.md](../deployment/self-hosted.md) |
| SoulOS Cloud | [cloud.md](../deployment/cloud.md) |

## Docs index

[docs/README.md](../README.md)
