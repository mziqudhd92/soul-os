# Tutorials — start here

**Recommended first tutorial:** **[Python bot integration](../guides/python-bot.md)** — wire SoulOS into an existing bot (Discord, CLI, FastAPI) without rewriting your stack.

Same list appears online at **https://mziqudhd92.github.io/soul-os/** or in **Soul Studio** → **Tutorials** at http://localhost:8765.

## Learning path (recommended order)

| # | Time | Tutorial | You will learn |
|---|------|----------|----------------|
| **1** | 25 min | **[Python bot integration](../guides/python-bot.md)** | Replace static system prompts with soul + memory + `send_message` |
| 2 | 10 min | [Kernel smoke test (curl)](../getting-started/quickstart.md#path-a) | Register soul, ingest memory, SSE chat without code |
| 3 | 15 min | [Build your first soul (Wizard)](../../packages/soulos-studio/soulos_studio/content/tutorials/first-soul-wizard.md) | Create `.soul.json` in Studio without hand-editing JSON |
| 4 | 12 min | [Deploy and test chat](../../packages/soulos-studio/soulos_studio/content/tutorials/deploy-and-chat.md) | Deploy from Studio, watch HEXACO drift live |
| 5 | 15 min | [Support bot + dev twin](../getting-started/quickstart.md) | Two avatars, same kernel — only soul + memory differ |
| 6 | 10 min | [MCP in Cursor](../../examples/mcp/README.md) | IDE tools for memory and identity |
| 7 | 15 min | [MCP deep dive](../guides/mcp.md) | Full MCP tool surface and gateway auth |

## All tutorials by topic

### Integrations (start here)

| Tutorial | File |
|----------|------|
| **Python bot** (recommended first) | [python-bot.md](../guides/python-bot.md) |
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
