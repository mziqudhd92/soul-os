# Contributing to SoulOS

Thanks for helping improve SoulOS. This is an open-source monorepo (MIT kernel + SDK); SoulOS Cloud hosting is separate.

## Repository layout

```
packages/soulos-core/      # Kernel (FastAPI) — MIT
packages/soulos-gateway/   # Cloud gateway — proprietary ops layer
packages/soulos-sdk/       # @soulos/sdk (TS) + soulos-sdk (Python)
packages/soulos-studio/    # Soul Builder UI (pip install soulos-studio)
spec/soul.schema.json      # Soul file JSON Schema
examples/                  # Example souls + context
docs/                      # Documentation (see docs/README.md)
scripts/                   # Doc generators, utilities
```

## Development setup

```bash
git clone https://github.com/mziqudhd92/soul-os.git soulos && cd soulos
npm ci
docker compose up --build
# Studio: http://localhost:8765
# Kernel: http://localhost:8000
```

Kernel hot-reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Studio dev server only:

```bash
docker compose up soulos-kernel db ollama
pip install -e packages/soulos-studio
soulos-studio --kernel http://localhost:8000
```

## Tests

```bash
npm run test:all          # kernel + gateway + studio
npm run test:kernel
npm run test:gateway
npm run test:studio
```

Python packages need **3.12+**. Kernel tests use `packages/soulos-core/.venv` if present, else `python3`.

## Pull requests

1. Focused changes with a clear description
2. Run `npm run test:all` before opening PR
3. Update `docs/` if behavior or APIs change
4. Match existing code style; avoid unrelated refactors

## Documentation

- Index: [docs/README.md](docs/README.md)
- Soul contract: [spec/soul.schema.json](spec/soul.schema.json)
- AI / GEO: [llms.txt](llms.txt), [llms-full.txt](llms-full.txt), [docs/SOULOS_AGENT_CONTEXT.md](docs/SOULOS_AGENT_CONTEXT.md)
- Update docs when changing APIs, ports (`8000` kernel, `8765` Studio, `/mcp/sse`), or MCP tools

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
