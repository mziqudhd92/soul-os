# Plug in SoulOS

SoulOS integrates into **any stack** (Docker, AWS, GCP, existing LLM apps). Pick an **integration mode** and an **inference plug-in**.

**Already have Bedrock/OpenAI + SSE?** → [Integrating as a sidecar](sidecar-integration.md) (recommended for co-pilots, control rooms, planners).

## 5-minute checklist

1. Run kernel + Postgres (+ inference): `docker compose up`, [sidecar compose](../../docker-compose.sidecar.yml), or a bridge profile below.
2. Register soul: `POST /v1/avatars/ensure` with `external_key` **or** Soul Studio.
3. Store `bot_id` per tenant/workspace in your DB (not always a global env var).
4. Preflight: `python scripts/soulos-doctor.py --kernel URL --inference URL --embedding-dimension N [--bot-id ID]`.
5. Wire **`SoulHybridClient`** (Python/TS) or [hybrid API](reference/hybrid-api.md).

## Hybrid API v0.2 (sidecars)

| Endpoint | Purpose |
|----------|---------|
| `GET /ready` | Runtime health for `SOULOS_ENABLED` fallback |
| `POST /hybrid/prepare` | One-call pre-turn: `system_prompt` + memories |
| `POST /hybrid/complete` | Ingest + `reflect_async` (202, non-blocking) |
| `POST /v1/avatars/ensure` | Idempotent register by `external_key` |

| Client | Import |
|--------|--------|
| Python | `from soulos import SoulHybridClient` |
| TypeScript | `import { SoulHybridClient } from "@soulos/sdk"` |

Docs: [sidecar integration](sidecar-integration.md) · [hybrid API schemas](reference/hybrid-api.md) · [compose example](../../examples/sidecar-compose/)

## Integration modes

| Mode | Use when | Your app keeps | SoulOS provides |
|------|----------|----------------|-----------------|
| **Sidecar / hybrid** | Existing LLM + SSE (Bedrock, OpenAI, LiteLLM) | Chat stream + tools | `hybrid/prepare` + `hybrid/complete` |
| **Full chat** | New bot, support widget | Thin client | `POST /chat/generate` SSE + MSV |
| **MCP only** | Cursor / Claude agents | IDE workflow | `ingest_memory`, `retrieve_memory`, `get_identity` |

## Inference plug-ins

SoulOS kernel calls **Ollama-shaped HTTP** (`/api/generate`, `/api/embeddings`). See [inference.md](../deployment/inference.md).

| Infra | Command | `EMBEDDING_DIMENSION` |
|-------|---------|-------------------------|
| Docker + Ollama | `docker compose up` | `768` |
| Mock (CI) | `--profile bridge-mock` | `768` |
| AWS Bedrock | `--profile bridge-aws` | `1024` |
| GCP Vertex | `--profile bridge-vertex` | `768` |

Copy [.env.example](../../.env.example). **Never** set `INFERENCE_API_URL` to OpenAI/Bedrock `/v1` URLs.

**Sidecar tip:** `INFERENCE_MODE=embeddings_only` — kernel embeds + lightweight reflect; your app owns chat LLM.

## Ports

| Service | Typical host port | Docker internal |
|---------|-------------------|-----------------|
| Your API | `8000` / `7000` | `your-api:8000` |
| SoulOS kernel | `8001` or `8100` | `soulos-kernel:8000` |
| Inference bridge | `11434` | `soulos-inference-bridge:11434` |

## Multi-tenant `external_key` patterns

| Pattern | Example |
|---------|---------|
| Workspace | `workspace:{uuid}` |
| User | `user:{uuid}` |
| Product surface | `copilot:control-room` |

See [sidecar integration](sidecar-integration.md#multi-tenant-avatars-external_key).

## Examples

| Example | Path |
|---------|------|
| Sidecar + your compose | [examples/sidecar-compose](../../examples/sidecar-compose/) |
| Hybrid adapter reference | [examples/hybrid-orchestrator](../../examples/hybrid-orchestrator/) |
| Full chat support bot | [examples/support-bot](../../examples/support-bot/) |

## Related

- [Hybrid orchestrator](hybrid-orchestrator.md)
- [Gateway headers (prod)](gateway-headers.md)
- [Inference backends](../deployment/inference.md)
- [API reference](../reference/api.md)
