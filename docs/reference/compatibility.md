# Inference compatibility matrix

SoulOS kernel expects an **Ollama-compatible** inference plug-in at `INFERENCE_API_URL` (typically port 11434).

| Backend | Compose profile | Chat | Embeddings | Notes |
|---------|-----------------|------|------------|-------|
| **bridge-mock** | `bridge-mock` | Mock | Deterministic 768-dim | CI / hybrid smoke default |
| **Ollama** | `ollama` | Yes | `nomic-embed-text` | Local dev full stack |
| **AWS Bedrock** | `bridge-aws` | Yes | Titan embed v2 | Set `BRIDGE_MODE=aws` |
| **GCP Vertex** | `bridge-vertex` | Yes | text-embedding-004 | Set `BRIDGE_MODE=vertex` |

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `INFERENCE_MODE` | `full` | Set `embeddings_only` for hybrid sidecar (no kernel chat) |
| `EMBEDDING_DIMENSION` | `768` | Must match bridge/embed model output |
| `INFERENCE_API_URL` | `http://ollama:11434` | Kernel → inference plug-in |
| `INFERENCE_SKIP_PULL` | `0` | `1` in sidecar compose to skip model pull |

## Hybrid sidecar smoke

```bash
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d
npm run smoke:hybrid
python scripts/soulos-doctor.py --kernel http://localhost:8001 --inference http://localhost:11434
```

## Dimension mismatches

If doctor reports embedding dimension mismatch, align `EMBEDDING_DIMENSION` on kernel and bridge. Kernel returns `MEMORY_DIM_MISMATCH` (422) when a live embedding length differs from config.

## Cloud inference

Production adopters (e.g. SignalPR) typically run `INFERENCE_MODE=embeddings_only` on SoulOS and keep chat on Bedrock/OpenAI in the app layer.

See [Sidecar integration](../guides/sidecar-integration.md) · [Inference deployment](../deployment/inference.md).
