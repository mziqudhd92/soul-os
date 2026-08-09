# Changelog

All notable changes to SoulOS are documented here.

## [Unreleased]

## [0.3.0] — 2026-08-09

### Added

- **Hybrid turn contracts** — optional reliability layer on the hybrid path (`runtime_config.turn_contract`):
  - Steps, required slots, intent `transitions` + `next`, `clear_slots_on_entry`, null-delete slot patches
  - `POST /hybrid/prepare` returns decoupled `contract_context` (`prompt_appendix`, `turn_version`, `ui_progress`, …) without mutating persona `system_prompt`
  - `POST /hybrid/complete` validates `filled_slots` / `intent` / `assistant_text` reject tokens; optimistic `expected_version` with DB compare-and-set; `idempotency_key` replay (preserves 202)
  - RFC 7807 codes: `TURN_CONTRACT_VIOLATION`, `TURN_REJECT_TOKEN`, `TURN_STEP_MISMATCH`, `TURN_STATE_STALE` (409), `TURN_SESSION_EXPIRED` (404) with `remedial_prompt_hint` / `invalid_slots`
  - `turn_sessions` table; TTL aligned with `MEMORY_SESSION_TTL_SECONDS` (lazy expire + `POST /memory/purge-expired` / session delete)
  - Payload bounds (64 KiB / depth 3 / 50 keys) at API boundary + resolver
  - Schema [`spec/turn-contract.schema.json`](spec/turn-contract.schema.json); CI `npm run test:turn-contracts` (quiet / octoner / try_everything / backtrack / retry_idempotency / expired_session)
  - SDKs: `merge_contract_into_system_prompt` / `mergeContractIntoSystemPrompt`; contract-mode auto `idempotency_key`
  - Docs: [turn-contracts.md](docs/guides/turn-contracts.md), tutorials [my-first-turn-contract](docs/tutorials/my-first-turn-contract.md) / [production](docs/tutorials/turn-contracts-production.md), [authority.md](docs/deployment/authority.md) + `deploy/authority.json`
- **Platform hygiene (roadmap P0–P2)** — OTel duration metrics + ops guide; session memory TTL; gateway Redis-backed rate limits; Helm chart (`deploy/helm/soulos`); LangChain hybrid example; TypeScript SDK vitest suite; architecture overview + non-goals docs
- **Vertical SoulPacks** — 23 MIT packs; Pages catalog with search + detail pages
- **Multi-agent teams (Phase A)** — app-orchestrated handoffs via `soulos.handoff`, packs `customer-front` / `inventory`, guide + examples
- **SoulPacks (M1–M5)** — in-repo MIT packs, `GET /v1/soulpacks`, `POST /v1/avatars/import-soulpack`, Studio gallery, `soulos pack` CLI

### Fixed

- Idempotent async `complete` replay preserves HTTP 202; hybrid test module deduplicated
- CI / MCP pin (`mcp>=1.0,<2`); SoulPacks path traversal hardening; GitHub Pages verify quoting

### Changed

- Adopters (incl. Getbyliner); AEO/GEO/SEO + SoulPacks catalog mirrors; project site `/soulpacks/`; MIT classifiers; dependency license inventory in CI
- OpenAPI artifact regenerated for hybrid contract fields
- Version bump to **0.3.0** (kernel, SDKs, schema, docs indexes)

### Removed

- Third-party persona registry import (ClawSouls bridge); SoulPacks remain MIT in-repo

## [0.2.0] — 2026-07-09

### Added

- **Hybrid-first docs** — README, `llms.txt`, and agent context lead with `ensure → prepare → LLM → complete`
- **RFC 7807 Problem Details** on `/ready`, hybrid, avatars, memory (`application/problem+json`, stable `code` field)
- **OpenAPI artifact** — `docs/reference/openapi.kernel.json` with CI drift check
- Soul Studio tutorials path, sidecar compose, dual-process chat telemetry

### Changed

- Hybrid sidecar positioned as primary integration path
