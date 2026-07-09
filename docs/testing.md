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
| `npm run test:sdk` | `packages/soulos-sdk/python/tests/` |
| `npm run doc:check` | Hybrid doc drift + OpenAPI lock + doc completeness |
| `npm run smoke:hybrid` | Sidecar ensure → prepare smoke (`scripts/hybrid-smoke.sh`) |
| `python3 scripts/soulos-eval.py` | Persona / hybrid eval harness |

Python packages need **3.12+**. Kernel tests prefer `packages/soulos-core/.venv` when present.

## TDD policy

- Write or update tests **before or alongside** behavior changes.
- **New public API or SDK surface** requires pytest coverage before merge.
- CI blocks merges on failing tests.

Product design docs under [docs/design/](design/README.md) are **not** the same as pytest TDD — see that README for naming.

## Where tests live

| Package | Tests |
|---------|--------|
| Kernel | `packages/soulos-core/test_*.py` — HTTP via `httpx.AsyncClient` + `ASGITransport`; pure logic without HTTP |
| Python SDK | `packages/soulos-sdk/python/tests/` — mock `httpx` / `_request`; assert RFC 7807 `SoulOSError` codes |
| TypeScript SDK | Parity documented; dedicated test suite tracked as a follow-up |
| Gateway / Studio / Bridge | Under each package’s test layout (see `npm run test:*`) |

## Conventions

- Kernel route tests: dependency overrides in `test_main.py` mocks.
- Persona / hybrid regressions: extend `test_persona_simple.py` or run `soulos-eval.py`.
- After API route changes: update tests **and** regenerate OpenAPI (`npm run openapi:export`), then `npm run doc:check`.

## See also

- [CONTRIBUTING.md](../CONTRIBUTING.md) — PR and docs checklists
- [Troubleshooting](guides/troubleshooting.md) — runtime errors by `code`
