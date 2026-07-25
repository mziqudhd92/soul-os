# Changelog

All notable changes to SoulOS are documented here. Version **0.2.0** focuses on hybrid sidecar DX, RFC 7807 errors, OpenAPI-locked SDK contract, and OTel tracing.

## [Unreleased]

### Removed

- **Third-party persona registry import** — removed external registry bridge, gallery, examples, and docs. First-party MIT **SoulPacks** planned — see `docs/guides/persona-packs.md`.

### Added

- MIT `license` + classifiers on all Python `pyproject.toml` packages
- Generated dependency license inventory (`docs/dependency-licenses.generated.md`) checked in CI
- CONTRIBUTING DCO note; OFL font vendoring note in `THIRD_PARTY_NOTICES.md`

## [0.2.0] — 2026-07-09

### Added

- **Hybrid-first docs** — README, `llms.txt`, and agent context lead with `ensure → prepare → LLM → complete`
- **RFC 7807 Problem Details** on `/ready`, hybrid, avatars, memory (`application/problem+json`, stable `code` field)
- **OpenAPI artifact** — `docs/reference/openapi.kernel.json` with CI drift check
- **`SoulHybridClient.run_turn()`** — thin Python wrapper over prepare/complete with Problem Details errors
- **`examples/fastapi-hybrid/`** — reference app with mock LLM and `GET /healthz`
- **OpenTelemetry spans** on hybrid prepare/complete (OpenInference-aligned attributes)
- **`persona_mode: simple`** — warmth/rigor/caution sliders → HEXACO mapping
- **Memory APIs** — `POST /memory/forget`, `DELETE /memory/session/{bot_id}/{session_id}`
- **Studio turn inspector** — export last prepare payload as JSON/curl
- **`scripts/hybrid-smoke.sh`** / `npm run smoke:hybrid`
- **Identity model guide** — `docs/guides/identity-model.md`
- **Compatibility matrix** — `docs/reference/compatibility.md`
- **Adopter playbooks** — SignalPR hybrid, Aeterna memory
- **Eval stub** — `scripts/soulos-eval.py`
- **MCP security** — full blast-radius table in SECURITY.md

### Changed

- **Breaking for error parsers:** clients that only read `{detail}` must also handle Problem Details shape (`type`, `title`, `status`, `detail`, `code`)
- `/ready` returns 503 Problem Details when degraded (was JSON body with 503)
- Embedder dimension mismatch returns 422 `MEMORY_DIM_MISMATCH` (was 500)

### Migration

```python
# Before
except httpx.HTTPStatusError as e:
    detail = e.response.json()["detail"]

# After
body = e.response.json()
code = body.get("code", "UNKNOWN")
detail = body.get("detail", str(body))
```

Hybrid API request/response shapes are stable for v0.2; no version header required yet.

## [0.1.0] — prior

Initial open-source release: kernel, Studio, MCP, full-chat SSE, hybrid sidecar API.
