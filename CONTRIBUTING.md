# Contributing to SoulOS

Thanks for helping improve SoulOS. This is an open-source monorepo (MIT kernel + SDK); SoulOS Cloud hosting is separate.

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

**Developer Certificate of Origin (DCO):** By contributing, you certify that you have the right to submit the contribution under the project's [MIT License](LICENSE), and that you grant SoulOS the right to distribute it under that license (see [DCO 1.1](https://developercertificate.org/)).

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

Sidecar hybrid smoke (mock bridge):

```bash
npm run smoke:hybrid
```

## Tests

Write or update tests **before or alongside** behavior changes — CI blocks merges on failing tests. See [docs/testing.md](docs/testing.md) for package layout and TDD policy.

```bash
npm run test:all          # kernel + bridge + gateway + studio + sdk
npm run test:kernel
npm run test:bridge
npm run test:gateway
npm run test:studio
npm run test:sdk
npm run doc:check         # hybrid drift + OpenAPI lock + doc completeness
npm run openapi:export    # regenerate docs/reference/openapi.kernel.json
npm run smoke:hybrid      # sidecar prepare → mock reply → complete
```

Python packages need **3.12+**. Kernel tests use `packages/soulos-core/.venv` if present, else `python3`.

**TDD:** new public API or SDK surface requires pytest coverage before merge.

## Pull requests

1. Focused changes with a clear description
2. Run `npm run test:all` and `npm run doc:check` before opening PR
3. Update `docs/` if behavior or APIs change (see checklist below)
4. Match existing code style; avoid unrelated refactors

### Documentation checklist (API or behavior changes)

- [ ] Updated reference ([api.md](docs/reference/api.md) and/or [hybrid-api.md](docs/reference/hybrid-api.md))
- [ ] Regenerated [openapi.kernel.json](docs/reference/openapi.kernel.json) if routes/schemas changed (`npm run openapi:export`)
- [ ] Updated [llms.txt](llms.txt) + [SOULOS_AGENT_CONTEXT.md](docs/SOULOS_AGENT_CONTEXT.md) if primary integration paths changed
- [ ] Added/updated tests (see [docs/testing.md](docs/testing.md))
- [ ] [CHANGELOG.md](CHANGELOG.md) entry under `[Unreleased]` or version section

### Release checklist (maintainers)

1. Bump `package.json` / SDK versions
2. Finalize CHANGELOG date + tag
3. Run `npm run doc:check` + `npm run test:all`
4. Verify README badges and [adopters](docs/adopters.md) unchanged unless intentional

## Labels for contributors

- `good first issue` — small, well-scoped (often docs or examples)
- `help wanted` — maintainers welcome external PRs

Suggested doc/example tasks to label `good first issue` when filing:

1. Add a TypeScript `runTurn()` smoke test mirroring Python SDK hybrid tests
2. Optional CI markdown link check (`lychee`) on `docs/**/*.md`
3. Expand Studio tutorial sync notes when GitHub Pages content drifts
4. Add a short GIF/screenshot to [my-first-sidecar.md](docs/tutorials/my-first-sidecar.md)
5. Document one more adopter playbook under `docs/playbooks/`

## Documentation

- Index: [docs/README.md](docs/README.md)
- Testing: [docs/testing.md](docs/testing.md)
- Soul contract: [spec/soul.schema.json](spec/soul.schema.json)
- AI / GEO: [llms.txt](llms.txt), [llms-full.txt](llms-full.txt), [docs/SOULOS_AGENT_CONTEXT.md](docs/SOULOS_AGENT_CONTEXT.md)
- Support: [SUPPORT.md](SUPPORT.md)
- Update docs when changing APIs, ports (`8000` kernel, `8765` Studio, `/mcp/sse`), or MCP tools

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
