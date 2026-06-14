# Inference backends

SoulOS kernel inference is **Ollama-native**, not OpenAI Chat Completions.

## Contract

| Operation | Endpoint |
|-----------|----------|
| Health | `GET {INFERENCE_API_URL}` |
| Chat (stream) | `POST /api/generate` |
| Embeddings | `POST /api/embeddings` |
| Model pull (boot) | `POST /api/pull` |

Setting `INFERENCE_API_URL=https://.../v1` (OpenAI or Bedrock Mantle) **will not work** without an [inference bridge](../../packages/soulos-inference-bridge/).

## Plug-in matrix

| Backend | `BRIDGE_MODE` | Typical embed dims | Env |
|---------|---------------|-------------------|-----|
| Ollama (local) | — (no bridge) | `768` (`nomic-embed-text`) | `INFERENCE_API_URL=http://ollama:11434` |
| Bridge mock | `mock` | `768` | `INFERENCE_SKIP_PULL=1` |
| AWS Bedrock | `bedrock` | `1024` (Titan V2) | `AWS_REGION`, `BEDROCK_*_MODEL_ID` |
| GCP Vertex | `vertex` | `768` (`text-embedding-004`) | `VERTEX_PROJECT_ID`, `VERTEX_LOCATION` |

Kernel env (align with backend):

| Variable | Default | Purpose |
|----------|---------|---------|
| `INFERENCE_API_URL` | `http://ollama:11434` | Inference base URL |
| `EMBEDDING_DIMENSION` | `768` | pgvector column + distance query |
| `INFERENCE_SKIP_PULL` | `0` | Set `1` for bridge / cloud (no Ollama pull) |
| `MODEL_NAME` | `llama3` | Passed to `/api/generate` |
| `EMBED_MODEL_NAME` | `nomic-embed-text` | Passed to `/api/embeddings` |

## Docker profiles

```bash
# Default: Ollama
docker compose up soulos-kernel db ollama

# Mock bridge (CI / no GPU)
docker compose --profile bridge-mock up soulos-kernel db soulos-inference-bridge

# AWS Bedrock (requires credentials)
docker compose --profile bridge-aws up soulos-kernel db soulos-inference-bridge

# GCP Vertex (requires VERTEX_PROJECT_ID + ADC)
docker compose --profile bridge-vertex up soulos-kernel db soulos-inference-bridge
```

See [.env.example](../../.env.example) for full variable sets.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| 404 on `/api/generate` | OpenAI/Bedrock `/v1` URL | Use Ollama or inference bridge |
| Embedding length error | Dim mismatch | Match `EMBEDDING_DIMENSION` to model |
| Stuck "Waiting for inference API" | Wrong URL / service down | `curl $INFERENCE_API_URL` |
| Slow first boot | `api/pull` downloading models | Use bridge + `INFERENCE_SKIP_PULL=1` |
| Hybrid app memory fails | LiteLLM URL on kernel | Kernel needs its own inference for embeddings |

Preflight: `python scripts/soulos-doctor.py --embedding-dimension 768`

## Custom bridge

Implement the four endpoints above in your own service if you need private networking, custom auth, or org-specific Bedrock/Vertex wiring. Contract reference: [packages/soulos-inference-bridge](../../packages/soulos-inference-bridge/).
