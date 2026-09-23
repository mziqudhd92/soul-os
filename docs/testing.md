# Testing SoulOS

Human-facing guide for running and writing tests. Agent-oriented notes also live in [AGENTS.md](../AGENTS.md).

## Commands

| Command | Scope |
|---------|--------|
| `npm run test:all` | Kernel + bridge + gateway + studio + Python SDK |
| `npm run test:kernel` | `packages/soulos-core/test_*.py` |
| `npm run test:bridge` | Inference bridge tests |
| `npm run test:gateway` | Gateway tests |
| `npm run test:studio` | Soul Studio tests |
| `npm run test:sdk` | Python SDK + TypeScript SDK (`@soulos/sdk`) |
| `npm run test:integration` | Kernel vs real Postgres/pgvector (`@pytest.mark.integration`) |
| `npm run test:coverage` | **≥85%** line coverage gate (kernel, gateway, bridge, studio, Python SDK) |
| `npm run lint` | Ruff + TypeScript `tsc --noEmit` |
| `npm run setup` | Create root `.venv` + install all packages editable |
| `npm run doc:check` | Hybrid doc drift + OpenAPI lock + SDK coverage + completeness |
| `npm run smoke:hybrid` | Sidecar ensure → prepare smoke (`scripts/hybrid-smoke.sh`) |
| `python3 scripts/soulos-eval.py` | Persona / hybrid eval harness |

Python packages need **3.12+**. Prefer `npm run setup` (root `.venv`); package-local `.venv` still works for ad-hoc pytest.

## Coverage policy

CI runs `npm run test:coverage` on Python 3.12. Each package has a `.coveragerc` with `fail_under = 85` (tests omitted from the measured surface):

| Package | Config |
|---------|--------|
| Kernel | `packages/soulos-core/.coveragerc` |
| Gateway | `packages/soulos-gateway/.coveragerc` |
| Inference bridge | `packages/soulos-inference-bridge/.coveragerc` |
| Soul Studio | `packages/soulos-studio/.coveragerc` (`source = soulos_studio`) |
| Python SDK | `packages/soulos-sdk/python/.coveragerc` (`source = soulos`) |

Debug with a lower floor: `COV_FAIL_UNDER=80 npm run test:coverage`.

## TDD policy

- Write or update tests **before or alongside** behavior changes.
- **New public API or SDK surface** requires pytest coverage before merge.
- CI blocks merges on failing tests **and** coverage below 85%.

Product design docs under [docs/design/](design/README.md) are **not** the same as pytest TDD — see that README for naming.

## Where tests live

| Package | Tests |
|---------|--------|
| Kernel | `packages/soulos-core/test_*.py` — HTTP via `httpx.AsyncClient` + `ASGITransport`; pure logic without HTTP |
| Python SDK | `packages/soulos-sdk/python/tests/` — mock `httpx` / `_request`; assert RFC 7807 `SoulOSError` codes |
| TypeScript SDK | `packages/soulos-sdk/ts/tests/` (vitest) |
| Gateway / Studio / Bridge | Under each package’s test layout (see `npm run test:*`) |

## Conventions

- Kernel route tests: dependency overrides in `test_main.py` mocks.
- Persona / hybrid regressions: extend `test_persona_simple.py` or run `soulos-eval.py`.
- After API route changes: update tests **and** regenerate OpenAPI (`npm run openapi:export`), then `npm run doc:check`.

## See also

- [CONTRIBUTING.md](../CONTRIBUTING.md) — PR and docs checklists
- [Troubleshooting](guides/troubleshooting.md) — runtime errors by `code`
