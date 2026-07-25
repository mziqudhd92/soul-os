# SoulPacks

First-party, **MIT-licensed** persona packages shipped in this repository under [`packs/soulpacks/`](../../packs/soulpacks/).

**Licensing note:** Switched from ClawSouls to SoulPacks because of licensing issues — see [CHANGELOG](../../CHANGELOG.md).

**Delivery plan (TDD checklist):** [SoulPacks TDD plan](../design/soulpacks-tdd-plan.md) — single source of truth for M1–M5.

## Quick start

```bash
# List packs (kernel CLI)
cd packages/soulos-core && .venv/bin/python -m cli pack list

# Convert without writing to the DB
.venv/bin/python -m cli pack import support-agent --persist false

# Ensure into a running kernel
curl -s -X POST http://localhost:8000/v1/avatars/import-soulpack \
  -H 'content-type: application/json' \
  -d '{"pack_id":"companion","persist":true}'
```

Studio: open **SoulPacks** → Open in Studio or Deploy to kernel.

Sidecar seed: [examples/soulpack-sidecar](../../examples/soulpack-sidecar/README.md).

Multi-agent demo packs: `customer-front`, `inventory` — see [Multi-agent teams](multi-agent-teams.md) and [examples/multi-agent-handoff](../../examples/multi-agent-handoff/).

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/v1/soulpacks?q=` | List/search catalog |
| `POST` | `/v1/avatars/import-soulpack` | Compile; optional `persist`/`register` → ensure |

`external_key` defaults to `soulos:{pack_id}@{version}`.

Error codes: `SOULPACK_NOT_FOUND`, `SOULPACK_LICENSE_REJECTED`, `SOULPACK_INVALID`.

## Pack layout

```
packs/soulpacks/
  catalog.json
  _presets.yaml
  support-agent/       # one directory per pack id (unversioned singleton)
    pack.json          # license must be MIT; version is metadata only
    SOUL.md
    …
```

**Versioning (v1):** In-repo packs are **unversioned singletons** — `packs/soulpacks/{id}/` holds one pack. The `version` field in `pack.json` is metadata for `external_key` (`soulos:{id}@{version}`). Side-by-side `@1.0.0` / `@2.0.0` trees are not supported; bump `version` in place or replace the directory.

Import rejects any pack whose `license` is not exactly `MIT`.

**Path safety:** `files` entries must stay inside the pack directory (resolved under `SOULPACKS_ROOT`). Traversal (`..`, absolute paths) is rejected.

## MSV resolution precedence

Highest wins:

1. Explicit `baseline_msv` in `pack.json`
2. Named preset: request `msv_preset` or manifest `msv_preset` → `_presets.yaml`
3. `default_msv_dict()` (schema defaults — not a zero vector)

## Authoring

```bash
# Export a compiled pack to a directory
.venv/bin/python -m cli pack export companion -o /tmp/my-companion
```

Or author `pack.json` + markdown by hand, then `pack import`.
