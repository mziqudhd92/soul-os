# ClawSouls → SoulOS examples

Metadata and import helpers for [ClawSouls](https://clawsouls.ai) personas. SoulOS is **not affiliated with or endorsed by ClawSouls**.

This directory does **not** ship full persona text (upstream-licensed prose). Import at runtime or generate locally:

| Action | Command |
|--------|---------|
| Import via kernel | `POST /v1/avatars/import-clawsouls` |
| Generate local `.soul.json` | `./generate-examples.sh` |
| Browse catalog | Soul Studio → **ClawSouls** |

## Featured souls (metadata only)

See [catalog.json](catalog.json) — each entry includes SPDX `license` and `source_url`.

## Legal

- [ATTRIBUTION.md](ATTRIBUTION.md) — per-soul licenses and derivative-work terms
- [LICENSE-APACHE-2.0.txt](LICENSE-APACHE-2.0.txt) — Apache-2.0 reference for official souls
- [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) — repo-wide third-party summary

Generated `*.soul.json` files are derivative works. Do not commit or redistribute without complying with the upstream soul license.

## Register with curl

```bash
curl -s -X POST http://localhost:8000/v1/avatars/import-clawsouls \
  -H "Content-Type: application/json" \
  -d '{"owner":"clawsouls","name":"surgical-coder","persist":true}'
```

See [ClawSouls import guide](../../docs/guides/clawsouls-import.md).
