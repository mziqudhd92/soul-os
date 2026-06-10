# SoulOS documentation

Browse by topic. New here? Start with [Overview](getting-started/overview.md) or jump straight to a fast path below.

**For AI agents / GEO:** [llms.txt](../llms.txt) · [llms-full.txt](../llms-full.txt) · [SOULOS_AGENT_CONTEXT.md](SOULOS_AGENT_CONTEXT.md) · [AGENTS.md](../AGENTS.md)

## Fast paths

| Goal | Time | Doc |
|------|------|-----|
| Kernel smoke test | 5 min | [Quickstart — Path A](getting-started/quickstart.md#path-a) |
| MCP in Cursor | 5 min | [examples/mcp](../examples/mcp/README.md) |
| Full tutorial (support + dev twin) | 15 min | [Quickstart](getting-started/quickstart.md) |
| Tune `.soul.json` in browser | 10 min | [Soul Builder](getting-started/soul-builder.md) |

## Choose your integration

| Use case | Best choice | Doc |
|----------|-------------|-----|
| IDE agent (Cursor) managing memory / FAQ | **MCP** (`/mcp/sse`) | [MCP guide](guides/mcp.md) · [tool reference](reference/mcp-tools.md) |
| Your app or site chat widget | **@soulos/sdk** or REST | [Quickstart](getting-started/quickstart.md) · [Python bot](guides/python-bot.md) |
| Hand-tuning personality JSON | **Soul Studio** (:8765) | [Soul Builder](getting-started/soul-builder.md) |

## Getting started

| Doc | Description |
|-----|-------------|
| [Overview](getting-started/overview.md) | Stack, prerequisites, security basics |
| [Quickstart (15 min)](getting-started/quickstart.md) | Support bot vs dev twin — same kernel |
| [Soul Builder UI](getting-started/soul-builder.md) | Configure and export `.soul.json` locally |

## Guides

| Doc | Description |
|-----|-------------|
| [Python bot integration](guides/python-bot.md) | Add SoulOS to an existing Python bot |
| [Psychometrics cheat sheet](guides/psychometrics.md) | What HEXACO sliders do |
| [MCP integration](guides/mcp.md) | Claude / Cursor via Model Context Protocol |
| [MCP tools reference](reference/mcp-tools.md) | Tool schemas and parameters |

## Reference

| Doc | Description |
|-----|-------------|
| [API reference](reference/api.md) | REST endpoints + SSE events |
| [MCP tools](reference/mcp-tools.md) | Tool argument schemas |
| [Soul standard](reference/soul-standard.md) | `.soul.json` anatomy |
| [Architecture](reference/architecture.md) | Kernel, runtime pipeline, monorepo |

## Deployment

| Doc | Description |
|-----|-------------|
| [Deployment overview](deployment/README.md) | Self-host vs Cloud |
| [Self-hosted](deployment/self-hosted.md) | Docker, env vars, `REQUIRE_AUTH` |
| [SoulOS Cloud](deployment/cloud.md) | Gateway, API keys, tenants |

## Examples

| Folder | Description |
|--------|-------------|
| [examples/mcp](../examples/mcp/) | 5-min Cursor MCP workflow |
| [examples/support-bot](../examples/support-bot/) | Customer support soul |
| [examples/dev-twin](../examples/dev-twin/) | Developer assistant soul |
| [examples/companion](../examples/companion/) | Personal companion soul |

## Regenerating architecture docs

From repo root:

```bash
python3 scripts/doc-gen/generate_docs.py
```

**Repo map:** [packages/README.md](../packages/README.md) · [scripts/README.md](../scripts/README.md)

Contributing and security: [CONTRIBUTING.md](../CONTRIBUTING.md) · [SECURITY.md](../SECURITY.md)
