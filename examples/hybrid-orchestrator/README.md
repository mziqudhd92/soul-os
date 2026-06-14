# Hybrid orchestrator pattern

Use SoulOS for **persistent soul + episodic memory** while your app keeps **LiteLLM / OpenAI tools + custom SSE**.

## Recommended client

Use **`SoulHybridClient`** from the Python SDK (or copy `soul_client.py` below):

```python
from soulos import SoulHybridClient

soul = SoulHybridClient(base_url="http://localhost:8001", bot_id=os.getenv("SOULOS_BOT_ID"))
if await soul.is_ready():
    ctx = await soul.prepare_turn(user_message, session_id=session_id)
    system_prompt = ctx["system_prompt"]
    # ... LiteLLM + your tools ...
    await soul.complete_turn(summary, user_message=user_message, session_id=session_id)
```

## Quick start

1. Sidecar stack: `docker compose -f docker-compose.sidecar.yml --profile bridge-mock up`
2. Register: `POST /v1/avatars/ensure` with `external_key` + soul JSON
3. Preflight: `python scripts/soulos-doctor.py --kernel http://localhost:8001 --bot-id <BOT_ID>`

## Hybrid API v0.2

| Endpoint | Purpose |
|----------|---------|
| `GET /ready` | Sidecar health (db + inference + embedding dim) |
| `POST /hybrid/prepare` | Identity + memories + `system_prompt` in one call |
| `POST /hybrid/complete` | Ingest summary + optional async reflect |
| `POST /v1/avatars/ensure` | Idempotent register by `external_key` |
| `POST /memory/*` | Optional `session_id` on ingest/retrieve |

## Docs

- [Plug in SoulOS](../../docs/guides/plug-in-soulos.md)
- [Hybrid orchestrator guide](../../docs/guides/hybrid-orchestrator.md)
- [Sidecar compose](../../docker-compose.sidecar.yml)
