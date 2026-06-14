# Plug in SoulOS

SoulOS integrates into **any stack** (Docker, AWS, GCP, existing LiteLLM apps). Pick an **integration mode** and an **inference plug-in**.

## 5-minute checklist

1. Run kernel + Postgres (+ inference): `docker compose up` or a bridge profile below.
2. Register a soul: `POST /v1/avatars` or Soul Studio.
3. Save `bot_id` in your app env (`SOULOS_BOT_ID`).
4. Run preflight: `python scripts/soulos-doctor.py`.
5. Wire SDK, REST, or `examples/hybrid-orchestrator/soul_client.py`.

## Integration modes

| Mode | Use when | Your app keeps | SoulOS provides |
|------|----------|----------------|-----------------|
| **Full chat** | New bot, support widget | Thin client | `POST /chat/generate` SSE + MSV |
| **Hybrid orchestrator** | Existing LLM + tools + custom SSE | Chat stream + tools | Identity, memory, `POST /state/reflect` |
| **MCP only** | Cursor / Claude agents | IDE workflow | `ingest_memory`, `retrieve_memory`, `get_identity` |

Hybrid guide: [hybrid-orchestrator.md](hybrid-orchestrator.md)

## Inference plug-ins

SoulOS kernel calls **Ollama-shaped HTTP** (`/api/generate`, `/api/embeddings`). See [inference.md](../deployment/inference.md).

| Infra | Command | `INFERENCE_API_URL` | `EMBEDDING_DIMENSION` |
|-------|---------|---------------------|------------------------|
| Docker + Ollama | `docker compose up` | `http://ollama:11434` | `768` |
| Mock (CI) | `docker compose --profile bridge-mock up soulos-kernel db soulos-inference-bridge` | `http://soulos-inference-bridge:11434` | `768` |
| AWS Bedrock | `docker compose --profile bridge-aws up ...` + AWS creds | bridge URL | `1024` |
| GCP Vertex | `docker compose --profile bridge-vertex up ...` + `VERTEX_PROJECT_ID` | bridge URL | `768` |

Copy [.env.example](../../.env.example) and uncomment the block for your plug-in.

**Do not** set `INFERENCE_API_URL` to OpenAI or Bedrock `/v1` URLs directly.

## Ports

| Service | Default port | Note |
|---------|--------------|------|
| Kernel | `8000` | REST + MCP |
| Your backend | your choice | Use kernel on `8001` if you already use `8000` |
| Inference (Ollama / bridge) | `11434` | Swappable via env |

## Examples

| Example | Path |
|---------|------|
| Full chat support bot | [examples/support-bot](../../examples/support-bot/) |
| Hybrid adapter (existing LLM + tools) | [examples/hybrid-orchestrator](../../examples/hybrid-orchestrator/) |

## Related

- [Inference backends](../deployment/inference.md)
- [Self-hosted deployment](../deployment/self-hosted.md)
- [API reference](../reference/api.md)
