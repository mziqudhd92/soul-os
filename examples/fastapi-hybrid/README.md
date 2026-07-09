# FastAPI hybrid sidecar example

Reference app showing **ensure → prepare → your LLM → complete** with a mock LLM and `/healthz` for K8s/ECS.

## Prerequisites

- SoulOS sidecar stack running (kernel on `:8001` by default):

```bash
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d
```

## Run locally

```bash
pip install -e packages/soulos-sdk/python fastapi uvicorn httpx
export SOULOS_KERNEL_URL=http://localhost:8001
export SOULOS_EXTERNAL_KEY=my-app-demo
uvicorn app:app --reload --port 8100
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Local process + kernel `/ready` aggregate |
| `POST` | `/chat` | `{ "message": "...", "session_id": "optional" }` |

## Replace mock LLM

Edit `mock_llm()` in `app.py` to call Bedrock, OpenAI, or LiteLLM. Keep SoulOS on embeddings-only:

```bash
INFERENCE_MODE=embeddings_only docker compose -f docker-compose.sidecar.yml --profile bridge-mock up
```

## Merge with sidecar compose

Add this service to your compose file:

```yaml
  fastapi-hybrid:
    build: ./examples/fastapi-hybrid
    ports:
      - "8100:8100"
    environment:
      - SOULOS_KERNEL_URL=http://soulos-kernel:8000
    depends_on:
      - soulos-kernel
```

See [Sidecar integration](../../docs/guides/sidecar-integration.md) and [Identity model](../../docs/guides/identity-model.md).
