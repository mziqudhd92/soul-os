# Self-hosted deployment

Part of [Deployment overview](README.md). For managed API, see [SoulOS Cloud](cloud.md).

SoulOS supports **dual consumption** via `@soulos/sdk` / `soulos-sdk`.

## Docker Compose

Best for: OSS adopters, privacy, custom models, full kernel access.

```bash
docker compose up --build
```

Services:

| Service | Port | Role |
|---------|------|------|
| `soulos-kernel` | 8000 | FastAPI runtime |
| `soulos-studio` | 8765 | Soul Builder UI (optional) |
| `db` | 5432 | PostgreSQL + pgvector |
| `ollama` | 11434 | Local inference (default stack) |
| `soulos-inference-bridge` | 127.0.0.1:11434 | Ollama-compatible bridge (profiles: `bridge-mock`, `bridge-aws`, `bridge-vertex`, `bridge-openrouter`) |

Plug-in guide: [guides/plug-in-soulos.md](../guides/plug-in-soulos.md) · Inference: [inference.md](inference.md)

Preflight: `python scripts/soulos-doctor.py`

SDK (direct to kernel):

```typescript
const soul = new SoulOSClient({ baseUrl: 'http://localhost:8000' });
```

Soul Studio (browser):

```bash
pip install -e packages/soulos-studio && soulos-studio
# http://127.0.0.1:8765 — deploy + chat proxy to kernel
```

For custom frontends, point `@soulos/sdk` directly at `http://localhost:8000` or your gateway URL.

Environment variables for the kernel:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | postgres in docker | Avatar + memory storage |
| `INFERENCE_API_URL` | `http://ollama:11434` | LLM + embeddings (Ollama or bridge) |
| `EMBEDDING_DIMENSION` | `768` | pgvector embedding size |
| `INFERENCE_SKIP_PULL` | `0` | Set `1` when using cloud bridge |
| `MODEL_NAME` | `llama3` | Chat model |
| `EMBED_MODEL_NAME` | `nomic-embed-text` | Embedding model |
| `REQUIRE_AUTH` | `0` | Set `1` in Cloud — kernel rejects direct HTTP without gateway headers |
| `GATEWAY_SECRET` | (dev default) | Must match gateway; change in production |

### Security notes

- **Open mode** (`REQUIRE_AUTH=0`, default): any client with kernel access can use any `bot_id` — fine for solo local dev only.
- **Cloud mode** (`REQUIRE_AUTH=1`): kernel requires `X-SoulOS-Gateway-Secret` + `X-SoulOS-Account-Id` from the gateway; do not expose port 8000 publicly.
- **Studio**: local dev tool; do not expose port 8765 publicly without auth in production.
- **Content limits**: `MAX_MEMORY_CONTENT_CHARS` (default 32768) caps ingest / chat / hybrid text fields (REST and MCP).

### Upgrading from `senticore` database name

Compose defaults renamed the Postgres database from `senticore` to `soulos`. **Existing data volumes are not rewritten** — Postgres only creates `POSTGRES_DB` on first init. If you already have a `postgres_data` volume from an older install:

```bash
# Option A — rename in place (stop kernel first so nothing is connected)
docker compose stop soulos-kernel
docker compose exec db psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'senticore';"
docker compose exec db psql -U postgres -c 'ALTER DATABASE senticore RENAME TO soulos;'
docker compose start soulos-kernel

# Option B — keep the old name (no data move)
# Set in .env / compose override:
#   POSTGRES_DB=senticore
#   DATABASE_URL=postgresql+asyncpg://postgres:changeme_local_dev@db:5432/senticore
```

Fresh installs need no action.

### Backup and restore (Postgres)

Avatar identity (`bots.current_msv`, `baseline_msv`) and episodic memory live in Postgres (+ pgvector). Back up regularly:

```bash
# Dump (from host with network to the db container)
docker compose exec -T db pg_dump -U postgres soulos > soulos-$(date +%F).sql

# Restore into a fresh volume
docker compose exec -T db psql -U postgres -d soulos < soulos-YYYY-MM-DD.sql
```

After restore, kernel boot applies any pending schema migrations (`soulos db migrate` / startup `init_database`).

**Embedding dimension:** if you change `EMBEDDING_DIMENSION`, existing `episodic_memories.embedding` rows are not compatible — recreate the column / re-ingest (or restore a backup taken with the same dimension). Prefer fixing the dimension before production data accumulates.

### Schema migrations

Kernel schema is versioned in `soulos_schema_migrations`. Boot applies pending migrations; operators can also run:

```bash
soulos db status
soulos db migrate
```


## Kernel-only for site integrations

Support widgets on your site need only:

1. `soulos-kernel` + Postgres (+ inference provider)
2. `@soulos/sdk` in your frontend or backend

Soul Studio (`packages/soulos-studio`) is optional — personality tuning demo UI.

## pip install (kernel package)

```bash
cd packages/soulos-core
uv pip install -e .
uvicorn main:app --host 0.0.0.0 --port 8000
```
