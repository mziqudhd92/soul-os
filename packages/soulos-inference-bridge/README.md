# soulos-inference-bridge

Ollama-compatible HTTP bridge so SoulOS kernel can use **mock**, **AWS Bedrock**, or **GCP Vertex** inference.

## Modes

| `BRIDGE_MODE` | Requires |
|---------------|----------|
| `mock` | nothing |
| `bedrock` | AWS credentials, `AWS_REGION` |
| `vertex` | `VERTEX_PROJECT_ID`, GCP ADC |

## Run locally

```bash
cd packages/soulos-inference-bridge
pip install -e ".[dev]"
BRIDGE_MODE=mock uvicorn main:app --port 11434
```

Point SoulOS kernel:

```bash
INFERENCE_API_URL=http://localhost:11434
INFERENCE_SKIP_PULL=1
EMBEDDING_DIMENSION=768  # or 1024 for Titan V2
```

## Docker

```bash
docker compose --profile bridge-mock up soulos-inference-bridge
```

See [docs/deployment/inference.md](../../docs/deployment/inference.md).
