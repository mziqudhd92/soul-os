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
| `ollama` | 11434 | Local inference (optional) |

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
| `INFERENCE_API_URL` | `http://ollama:11434` | LLM + embeddings |
| `MODEL_NAME` | `llama3` | Chat model |
| `EMBED_MODEL_NAME` | `nomic-embed-text` | Embedding model |
| `REQUIRE_AUTH` | `0` | Set `1` in Cloud — kernel rejects direct HTTP without gateway headers |
| `GATEWAY_SECRET` | (dev default) | Must match gateway; change in production |

### Security notes

- **Open mode** (`REQUIRE_AUTH=0`, default): any client with kernel access can use any `bot_id` — fine for solo local dev only.
- **Cloud mode** (`REQUIRE_AUTH=1`): kernel requires `X-SoulOS-Gateway-Secret` + `X-SoulOS-Account-Id` from the gateway; do not expose port 8000 publicly.
- **Studio**: local dev tool; do not expose port 8765 publicly without auth in production.

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
