# SoulPacks — TDD delivery plan

**Status: complete (M1–M5 shipped).**

First-party, MIT-only persona packages. This is the **only** SoulPacks plan document in the repo (user guide: [persona-packs.md](../guides/persona-packs.md)).

**Why:** Switched from ClawSouls to SoulPacks because of licensing issues (upstream persona prose / derivative-work obligations). SoulPacks stay MIT in-repo — see [CHANGELOG.md](../../CHANGELOG.md) `[Unreleased]`.

## Identifiers

| Surface | Identifier |
|---------|------------|
| Product / Studio tab | SoulPacks |
| On-disk root | `packs/soulpacks/` |
| Kernel APIs | `GET /v1/soulpacks`, `POST /v1/avatars/import-soulpack` |
| Python module | `packages/soulos-core/runtime/soulpacks.py` |
| CLI | `soulos pack list\|import\|export` |
| `external_key` | `soulos:{pack_id}@{version}` |
| Error codes | `SOULPACK_NOT_FOUND`, `SOULPACK_LICENSE_REJECTED`, `SOULPACK_INVALID` |

No remote registry. Import rejects any pack whose manifest `license` is not exactly `MIT`.

**Layout (v1):** Unversioned singletons — `packs/soulpacks/{id}/` only (no `/{id}/{version}/`). Version in `pack.json` is metadata for `external_key`.

**MSV precedence:** explicit `baseline_msv` ≫ `msv_preset` / `_presets.yaml` ≫ `default_msv_dict()`.

**Security:** Pack `files` paths are resolved and must remain under the pack directory ⊆ `SOULPACKS_ROOT`. Export uses atomic temp-file + `os.replace` writes.

## Before → after

| Area | Before (ClawSouls) | After (SoulPacks) |
|------|--------------------|-------------------|
| Content source | `clawsouls.ai` API + Soul Spec | In-repo MIT packs under `packs/soulpacks/` |
| License model | Upstream Apache/MIT/CC-BY; derivatives | Pack + SoulOS code all MIT |
| Kernel import | `POST /v1/avatars/import-clawsouls` | `POST /v1/avatars/import-soulpack` |
| Kernel list | Studio → external API | `GET /v1/soulpacks` (+ optional `?q=`) |
| Studio UI | External gallery tab | **SoulPacks** tab |
| Studio proxy | `/api/clawsouls/*` | `/api/soulpacks`, `/api/soulpacks/import` |
| MSV | External-linked presets YAML | Pack-owned `baseline_msv` and/or `packs/soulpacks/_presets.yaml` |
| Idempotent key | `clawsouls:{owner}/{name}@{ver}` | `soulos:{pack_id}@{version}` |
| Convert-only | `persist: false` | Same |
| Examples | External registry examples/scripts | `examples/soulpack-sidecar/`, `soulos pack` CLI |
| Docs / notices | Upstream attribution | SoulPacks guide + CI license gate |

## Global TDD rules

- Every milestone: **write failing tests → implement → green → regenerate OpenAPI / docs as needed**.
- Kernel HTTP: `httpx.AsyncClient` + `ASGITransport(app=app)`.
- Pure compile: `packages/soulos-core/test_soulpacks.py` + fixtures.
- CI: `npm run test:kernel` (+ studio) + `npm run doc:check` + license `--fail-on-copyleft`.

---

## Detailed todo list

### M1 — Format + compile (pure logic) — DONE

- [x] Fixtures under `packages/soulos-core/fixtures/soulpacks/`
- [x] `test_soulpacks.py` (catalog, merge, MSV, MIT reject, external_key, validate)
- [x] `runtime/soulpacks.py` (`list_packs`, `load_pack`, `compile_pack`, `default_external_key`)
- [x] Seed `packs/soulpacks/` + `_presets.yaml` + `support-agent`
- [x] `SOULPACKS_ROOT` env override

### M2 — Kernel HTTP import/list — DONE

- [x] `test_soulpacks_api.py` (list, filter, persist false/true, 404, license 422, `register` alias)
- [x] `ImportSoulPackRequest` + routes in `main.py`
- [x] Error codes in `runtime/errors.py`
- [x] OpenAPI + hybrid docs + `llms-full.txt`

### M3 — Studio SoulPacks gallery — DONE

- [x] Studio proxy tests + SoulPacks nav smoke
- [x] `/api/soulpacks`, `/api/soulpacks/import`
- [x] Gallery UI (Open / Deploy)

### M4 — Ship content + sidecar example — DONE

- [x] ≥3 MIT packs: `support-agent`, `companion`, `dev-twin`
- [x] `test_each_catalog_pack_compiles` / catalog MIT check
- [x] `examples/soulpack-sidecar/` + seed dry-run test
- [x] User guide + README path
- [x] Docker copies `packs/soulpacks` (`SOULPACKS_ROOT`)

### M5 — Authoring DX (export + CLI) — DONE

- [x] `export_pack` + export MIT stamp tests
- [x] `soulos pack list|import|export` + CLI tests
- [x] Documented in user guide

### Out of scope

- [x] ~~Re-proxy external persona registries~~ (will not do)
- [x] ~~Non-MIT pack allowlists~~ (will not do)
- [x] ~~Marketplace billing for packs v1~~ (will not do)

### Review checklist

- [x] Name **SoulPacks** for APIs + Studio
- [x] Packs at repo-root `packs/soulpacks/`
- [x] M1→M5 delivered with tests green
- [x] License story: SoulOS + SoulPacks = MIT only
- [x] Consolidated to this single plan document
