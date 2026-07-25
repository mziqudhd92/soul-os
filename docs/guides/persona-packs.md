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
  support-agent/
    pack.json          # license must be MIT
    SOUL.md
    …
```

Import rejects any pack whose `license` is not exactly `MIT`.

## Authoring

```bash
# Export a compiled pack to a directory
.venv/bin/python -m cli pack export companion -o /tmp/my-companion
```

Or author `pack.json` + markdown by hand, then `pack import`.
