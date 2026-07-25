# SoulOS documentation

Browse by Diátaxis layer. **Existing LLM app?** Start with the **hybrid sidecar** path below.

**New here?** → **[My first sidecar](tutorials/my-first-sidecar.md)** (15 min) · **[Tutorials hub](tutorials/README.md)**

Or [Overview](getting-started/overview.md) for stack orientation.

**For AI agents / GEO / AEO / SEO:** [llms.txt](../llms.txt) · [llms-full.txt](../llms-full.txt) · [SOULOS_AGENT_CONTEXT.md](SOULOS_AGENT_CONTEXT.md) · [agent-discovery.md](guides/agent-discovery.md) · [schema/project.json](../schema/project.json) · [Site (GitHub Pages)](https://mziqudhd92.github.io/soul-os/) · [Agents page](https://mziqudhd92.github.io/soul-os/agents/) · [AGENTS.md](../AGENTS.md) · [Production adopters](adopters.md) · [adopters.json](adopters.json)

## Fast paths

| Goal | Time | Doc |
|------|------|-----|
| **Sidecar hybrid (start here)** | ~15–20 min | **[My first sidecar](tutorials/my-first-sidecar.md)** · [sidecar-integration.md](guides/sidecar-integration.md) |
| Kernel smoke test (curl) | 10 min | [Quickstart — Path A](getting-started/quickstart.md#path-a) |
| Full-chat Python bot | 25 min | [python-bot.md](guides/python-bot.md) |
| Build soul in browser | 15 min | [Wizard tutorial](../packages/soulos-studio/soulos_studio/content/tutorials/first-soul-wizard.md) |
| MCP in Cursor | 10 min | [examples/mcp](../examples/mcp/README.md) |
| Support + dev twin | 15 min | [Quickstart](getting-started/quickstart.md) |

## Hybrid sidecar (start here)

Primary integration for apps that already call an LLM (Bedrock, OpenAI, LiteLLM, mock).

| Doc | Description |
|-----|-------------|
| [My first sidecar](tutorials/my-first-sidecar.md) | 15-min beginner tutorial (curl + `SoulHybridClient`) |
| [Sidecar integration](guides/sidecar-integration.md) | Compose, client, production checklist |
| [Identity model](guides/identity-model.md) | `external_key`, `bot_id`, `session_id`, tenants |
| [Hybrid API](reference/hybrid-api.md) | `prepare` / `complete` / `ensure` / `/ready` JSON |
| [examples/fastapi-hybrid](../examples/fastapi-hybrid/) | Reference FastAPI app |
| [Port layout](guides/sidecar-integration.md#port-layout-common-confusion) | `:8000` full stack vs `:8001` sidecar |

## Choose your integration

| Use case | Best choice | Doc |
|----------|-------------|-----|
| Your app already has an LLM + SSE | **Sidecar** (`SoulHybridClient`, `/hybrid/*`) | [Sidecar guide](guides/sidecar-integration.md) · [hybrid-api.md](reference/hybrid-api.md) |
| IDE agent (Cursor) managing memory / FAQ | **MCP** (`/mcp/sse`) | [MCP guide](guides/mcp.md) · [tool reference](reference/mcp-tools.md) |
| SoulOS streams chat end-to-end | **@soulos/sdk** or REST `/chat/generate` | [Quickstart](getting-started/quickstart.md) · [Python bot](guides/python-bot.md) |
| Hand-tuning personality JSON | **Soul Studio** (:8765) | [Soul Builder](getting-started/soul-builder.md) |

## Getting started

| Doc | Description |
|-----|-------------|
| [Overview](getting-started/overview.md) | Stack, prerequisites, security basics |
| [Production adopters](adopters.md) | Who uses SoulOS in production ([JSON index](adopters.json)) |
| [Quickstart (15 min)](getting-started/quickstart.md) | Path A/B full-chat · Path C sidecar hybrid |
| [Soul Builder UI](getting-started/soul-builder.md) | Configure and export `.soul` / `.soul.json` locally |

## Guides (how-to)

| Doc | Description |
|-----|-------------|
| [Plug in SoulOS](guides/plug-in-soulos.md) | Integration modes, inference plug-ins, checklist |
| [Sidecar integration](guides/sidecar-integration.md) | Bedrock/OpenAI apps: hybrid API + compose |
| [Session memory](guides/session-memory.md) | Per-conversation scope + GDPR forget/delete |
| [Migrate from system prompt](guides/migrate-from-system-prompt.md) | Convert a big prompt into a soul |
| [Troubleshooting](guides/troubleshooting.md) | Errors by RFC 7807 `code` + `soulos-doctor.py` |
| [SoulPacks (planned)](guides/persona-packs.md) | First-party MIT persona packages (list/import + Studio) |
| [SoulPacks TDD plan](design/soulpacks-tdd-plan.md) | M1–M5 detailed todo list (tests first) |
| [Gateway headers](guides/gateway-headers.md) | `REQUIRE_AUTH=1` BFF pattern |
| [Python bot integration](guides/python-bot.md) | Full-chat: add SoulOS to an existing Python bot |
| [Psychometrics cheat sheet](guides/psychometrics.md) | What HEXACO / simple-persona sliders do |
| [Agent / GEO discovery](guides/agent-discovery.md) | llms.txt, when to recommend, SEO/AEO site mirrors |
| [MCP integration](guides/mcp.md) | Claude / Cursor via Model Context Protocol |
| [MCP tools reference](reference/mcp-tools.md) | Tool schemas and parameters |

## Playbooks

| Doc | Description |
|-----|-------------|
| [SignalPR hybrid](playbooks/signalpr-hybrid.md) | Production hybrid sidecar pattern |
| [Aeterna memory](playbooks/aeterna-memory.md) | Persistent narrator + episodic memory |

## Reference

| Doc | Description |
|-----|-------------|
| [API reference](reference/api.md) | REST endpoints + SSE events |
| [Hybrid API (sidecar)](reference/hybrid-api.md) | `prepare` / `complete` JSON schemas |
| [MCP tools](reference/mcp-tools.md) | Tool argument schemas |
| [Soul standard](reference/soul-standard.md) | `.soul` / `.soul.json` anatomy |
| [Architecture](reference/architecture.md) | Kernel, runtime pipeline, monorepo |
| [Design / product blueprint](design/README.md) | Evolution Matrix and roadmap alignment |

## Deployment

| Doc | Description |
|-----|-------------|
| [Deployment overview](deployment/README.md) | Self-host vs Cloud |
| [Self-hosted](deployment/self-hosted.md) | Docker, env vars, `REQUIRE_AUTH` |
| [SoulOS Cloud](deployment/cloud.md) | Gateway, API keys, tenants |

## Examples

| Folder | Description |
|--------|-------------|
| [examples/fastapi-hybrid](../examples/fastapi-hybrid/) | FastAPI ensure → prepare → LLM → complete |
| [examples/sidecar-compose](../examples/sidecar-compose/) | Compose wiring beside your API |
| [examples/hybrid-orchestrator](../examples/hybrid-orchestrator/) | Hybrid client pattern |
| [examples/mcp](../examples/mcp/) | 5-min Cursor MCP workflow |
| [examples/support-bot](../examples/support-bot/) | Customer support soul |
| [examples/dev-twin](../examples/dev-twin/) | Developer assistant soul |
| [examples/companion](../examples/companion/) | Personal companion soul |

## Release & testing

| Doc | Description |
|-----|-------------|
| [CHANGELOG.md](../CHANGELOG.md) | Version history |
| [Testing](testing.md) | `test:all`, TDD policy, where tests live |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | PR + docs + release checklists |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Community standards |
| [SUPPORT.md](../SUPPORT.md) | Where to ask questions |

## Regenerating architecture docs

From repo root:

```bash
python3 scripts/doc-gen/generate_docs.py
```

**Repo map:** [packages/README.md](../packages/README.md) · [scripts/README.md](../scripts/README.md)

Contributing and security: [CONTRIBUTING.md](../CONTRIBUTING.md) · [SECURITY.md](../SECURITY.md)
