# SoulPacks — TDD delivery plan

First-party, MIT-only persona packages that replace the removed external registry import.

**Why:** Switched from ClawSouls to SoulPacks because of licensing issues (upstream persona prose / derivative-work obligations). SoulPacks stay MIT in-repo — see [CHANGELOG.md](../../CHANGELOG.md) `[Unreleased]`.

**Guide (user-facing):** [persona-packs.md](../guides/persona-packs.md)

## Identifiers

| Surface | Identifier |
|---------|------------|
| Product / Studio tab | SoulPacks |
| On-disk root | `packs/soulpacks/` |
| Kernel APIs | `GET /v1/soulpacks`, `POST /v1/avatars/import-soulpack` |
| Python module | `packages/soulos-core/runtime/soulpacks.py` |
| `external_key` | `soulos:{pack_id}@{version}` |
| Error codes | `SOULPACK_NOT_FOUND`, `SOULPACK_LICENSE_REJECTED`, `SOULPACK_INVALID` |

No remote registry. Import rejects any pack whose manifest `license` is not exactly `MIT`.

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
| Examples | External registry examples/scripts | `examples/soulpack-sidecar/`, pack CLI |
| Docs / notices | Upstream attribution | SoulPacks guide + CI license gate |

## Global TDD rules

- Every milestone: **write failing tests → implement → green → regenerate OpenAPI / docs as needed**.
- Kernel HTTP: `httpx.AsyncClient` + `ASGITransport(app=app)` with overrides from `packages/soulos-core/test_main.py`.
- Pure compile: unit tests, fixtures under `packages/soulos-core/fixtures/soulpacks/`.
- CI: `npm run test:kernel` (+ studio when touched) + `npm run doc:check` + license `--fail-on-copyleft`.
- Do not reintroduce external-registry names in APIs or UI.

---

## Detailed todo list

### M1 — Format + compile (pure logic)

**Goal:** Load a MIT SoulPack from disk, merge markdown, resolve MSV, validate soul schema — no HTTP.

- [ ] Add `packages/soulos-core/fixtures/soulpacks/minimal/` (MIT `pack.json` + markdown)
- [ ] Add `packages/soulos-core/test_soulpacks.py` with failing tests:
  - [ ] `test_load_catalog_lists_support_agent`
  - [ ] `test_compile_merges_markdown_order`
  - [ ] `test_compile_applies_baseline_msv_from_pack`
  - [ ] `test_compile_applies_named_preset`
  - [ ] `test_compile_rejects_non_mit_license`
  - [ ] `test_compile_rejects_missing_soul_fields`
  - [ ] `test_default_external_key` → `soulos:support-agent@1.0.0`
  - [ ] `test_fixture_pack_roundtrip_validate`
- [ ] Implement `packages/soulos-core/runtime/soulpacks.py` (`list_packs`, `load_pack`, `compile_pack`, `default_external_key`)
- [ ] Seed `packs/soulpacks/catalog.json`, `_presets.yaml`, `support-agent/` (from `examples/support-bot`, MIT)
- [ ] Support `SOULPACKS_ROOT` env override for tests
- [ ] **Done when:** `pytest packages/soulos-core/test_soulpacks.py` green; no HTTP routes yet

### M2 — Kernel HTTP import/list

**Goal:** Restore import DX on the kernel.

- [ ] Add API tests (`test_soulpacks_api.py` or extend `test_soulpacks.py`):
  - [ ] `test_list_soulpacks_200`
  - [ ] `test_list_soulpacks_q_filter`
  - [ ] `test_import_persist_false`
  - [ ] `test_import_persist_true_ensure`
  - [ ] `test_import_unknown_pack_404` → `SOULPACK_NOT_FOUND`
  - [ ] `test_import_non_mit_422` → `SOULPACK_LICENSE_REJECTED`
  - [ ] `test_import_alias_register` (`register` ≡ `persist`)
- [ ] Add `ImportSoulPackRequest` in `packages/soulos-core/schemas.py`
- [ ] Add `GET /v1/soulpacks` + `POST /v1/avatars/import-soulpack` in `main.py`
- [ ] Add error codes in `runtime/errors.py`
- [ ] Regenerate `docs/reference/openapi.kernel.json`
- [ ] Update `docs/reference/hybrid-api.md`, `llms-full.txt`
- [ ] **Done when:** kernel tests + `npm run doc:check` green

### M3 — Studio SoulPacks gallery

**Goal:** Browse / Open in Studio / Deploy without leaving Studio.

- [ ] Studio tests:
  - [ ] `test_api_soulpacks_list_proxies_kernel`
  - [ ] `test_api_soulpacks_import_proxies_kernel`
  - [ ] Static smoke: `index.html` has SoulPacks nav
- [ ] Proxy routes in `soulos_studio/app.py` → kernel
- [ ] Gallery UI in `static/index.html` + `studio.js` + CSS
- [ ] Open (`persist: false` → form) / Deploy (`persist: true` → avatar id)
- [ ] **Done when:** studio pytest green; manual list → open → deploy works

### M4 — Ship content + sidecar example

**Goal:** Usable MIT packs and a seed path for hybrid.

- [ ] Tests:
  - [ ] `test_catalog_has_at_least_three_mit_packs`
  - [ ] `test_each_catalog_pack_compiles`
  - [ ] `test_seed_script_dry_run`
- [ ] Ship MIT packs: `support-agent`, `companion`, `dev-twin`
- [ ] Add `examples/soulpack-sidecar/` (seed + README)
- [ ] Expand user guide `docs/guides/persona-packs.md`
- [ ] README path: “Use a SoulPack” → guide + Studio tab
- [ ] Confirm `THIRD_PARTY_NOTICES.md` describes first-party MIT SoulPacks
- [ ] **Done when:** compile-all + doc completeness green

### M5 — Authoring DX (export + CLI)

**Goal:** Create packs from Studio/CLI without hand-editing forever.

- [ ] Tests:
  - [ ] `test_export_soul_to_pack_dir`
  - [ ] `test_cli_pack_list`
  - [ ] `test_cli_pack_import_persist_false`
  - [ ] `test_export_rejects_if_license_not_mit` (export always MIT)
- [ ] `export_pack(soul, out_dir)` in `runtime/soulpacks.py`
- [ ] Studio “Export as SoulPack”
- [ ] CLI: `list` / `import` / `export` (`cli.py` or `scripts/soulpack.py`)
- [ ] Document in SoulPacks guide
- [ ] **Done when:** export → re-import roundtrip test green

### Out of scope

- [x] ~~Re-proxy external persona registries~~ (will not do)
- [x] ~~Non-MIT pack allowlists~~ (will not do)
- [x] ~~Marketplace billing for packs v1~~ (will not do)

### Review checklist

- [x] Name **SoulPacks** for APIs + Studio
- [x] Packs at repo-root `packs/soulpacks/` (v1)
- [ ] M1→M5 order; no Studio until M2 APIs exist
- [ ] Every milestone merges only with new tests green
- [ ] License story: SoulOS + SoulPacks = MIT only
