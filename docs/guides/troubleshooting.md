# Troubleshooting SoulOS

Keyed by RFC 7807 `code` from `application/problem+json` responses. Prefer searching the exact `code` string you see in logs.

**See also:** [API errors](../reference/api.md#5-errors-rfc-7807) · [Hybrid API](../reference/hybrid-api.md#errors-rfc-7807) · [Sidecar integration](sidecar-integration.md)

## Quick doctor

```bash
# Full stack
python3 scripts/soulos-doctor.py --kernel http://localhost:8000

# Sidecar
python3 scripts/soulos-doctor.py --kernel http://localhost:8001 \
  --inference http://localhost:11434 --embedding-dimension 768 --bot-id <BOT_ID>
```

Also: `curl -s http://localhost:8001/ready` — expect HTTP **200** with `"status":"ok"`. HTTP **503** with `code: READY_DEGRADED` means the kernel process is up but dependencies are not.

## By error `code`

### `READY_DEGRADED` (503)

`GET /ready` failed database or inference checks.

| Check | Fix |
|-------|-----|
| `checks.database` not ok | `docker compose` Postgres healthy; wait for migrations |
| `checks.inference` not ok | Start Ollama or bridge; set `INFERENCE_API_URL` |
| Wrong port | Sidecar kernel is often **:8001**, full stack **:8000** |

### `INFERENCE_DOWN` (503)

Embedder or chat inference unreachable during a request.

- Confirm bridge/Ollama: `curl -s "$INFERENCE_API_URL/api/tags"` (Ollama) or bridge health
- Sidecar mock: `docker compose -f docker-compose.sidecar.yml --profile bridge-mock up`
- Embedding model pull: `nomic-embed-text` (or your configured model)

### `MEMORY_DIM_MISMATCH`

Stored vectors and current embedder dimension disagree (e.g. switched models).

- Align `EMBEDDING_DIMENSION` with the embedder
- Fresh volume / re-ingest if you intentionally changed models
- Doctor prints expected dimension — match compose env

### `BOT_NOT_FOUND` (404)

Unknown `bot_id`.

- Re-run `POST /v1/avatars/ensure` with your `external_key`
- Confirm you are hitting the same kernel host/port that registered the bot

### `SOUL_INVALID` / `VALIDATION_ERROR` (422)

Soul payload failed schema or field validation.

- Compare with [spec/soul.schema.json](../../spec/soul.schema.json)
- HEXACO keys must be `H,E,X,A,C,O` in range `-1..1`
- Simple mode: send `persona_mode` + `simple_persona` on register; kernel derives `baseline_msv`

### `ACCESS_DENIED` (403)

Tenant / gateway auth rejected the call.

- Local: `REQUIRE_AUTH=0`
- Cloud/BFF: send gateway headers — [gateway-headers.md](gateway-headers.md)

### `CLAWSOULS_IMPORT_DISABLED`

Import endpoint disabled in this deployment — enable per [clawsouls-import.md](clawsouls-import.md) or generate souls offline.

### `INTERNAL_ERROR` (500)

Unexpected server failure — check kernel logs; open a bug with doctor output ([SUPPORT.md](../../SUPPORT.md)).

## Common non-code issues

| Symptom | Fix |
|---------|-----|
| Connection refused | `docker compose up`; wait for healthy |
| Empty / generic answers | Ingest memory; check prepare `memories` |
| Memory not recalled turn 2 | Pass same `session_id`; call `complete` after turn 1 |
| Forget / session delete missing in MCP | **REST-only** in v0.2 — [session-memory.md](session-memory.md) |
| Studio export missing `persona_mode` | Expected — authoring fields stripped after derive |

## Still stuck?

1. Run `soulos-doctor.py` and save stdout
2. Capture one failing response body (`code`, `detail`, `status`)
3. Note compose file (`docker-compose.yml` vs `docker-compose.sidecar.yml`) and kernel version / commit
4. Open an issue with the [bug report template](../../.github/ISSUE_TEMPLATE/bug_report.yml)
