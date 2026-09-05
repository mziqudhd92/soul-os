# soulos-inference-bridge

Ollama-compatible HTTP bridge so SoulOS kernel can use **mock**, **AWS Bedrock**,
**GCP Vertex**, or **OpenRouter** inference.

## Modes

| `BRIDGE_MODE` | Requires |
|---------------|----------|
| `mock` | nothing |
| `bedrock` | AWS credentials, `AWS_REGION` |
| `vertex` | `VERTEX_PROJECT_ID`, GCP ADC |
| `openrouter` | `OPENROUTER_API_KEY` |

## Run locally

```bash
cd packages/soulos-inference-bridge
pip install -e ".[dev]"
BRIDGE_MODE=mock uvicorn main:app --port 11434
```

OpenRouter:

```bash
export OPENROUTER_API_KEY=sk-or-...
export BRIDGE_MODE=openrouter
export OPENROUTER_CHAT_MODEL=openai/gpt-4o-mini
# optional: OPENROUTER_EMBED_MODEL=openai/text-embedding-3-small
uvicorn main:app --port 11434
```

Point SoulOS kernel:

```bash
INFERENCE_API_URL=http://localhost:11434
INFERENCE_SKIP_PULL=1
EMBEDDING_DIMENSION=768  # or 1024 for Titan V2 / remote OpenRouter embeds
MODEL_NAME=openai/gpt-4o-mini  # when using OpenRouter
```

## Docker

```bash
docker compose --profile bridge-mock up soulos-inference-bridge
docker compose --profile bridge-openrouter up soulos-inference-bridge
```

See [docs/deployment/inference.md](../../docs/deployment/inference.md).
