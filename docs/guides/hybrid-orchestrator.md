# Hybrid orchestrator

Keep your **existing chat + tools + SSE**; use SoulOS for **soul + episodic memory**.

**Start here:** [Integrating as a sidecar](sidecar-integration.md) · [Hybrid API schemas](../reference/hybrid-api.md)

## Recommended flow (v0.2)

```python
from soulos import SoulHybridClient

soul = SoulHybridClient(base_url=os.getenv("SOULOS_KERNEL_URL"))
await soul.ensure_avatar("workspace:tenant-id", soul_json)

ctx = await soul.prepare_turn(user_message, session_id=session_id)
system_prompt = ctx["system_prompt"]
# ... your Bedrock / OpenAI / LiteLLM stream ...

await soul.complete_turn(summary, user_message=user_message, session_id=session_id, reflect_async=True)
```

TypeScript: `SoulHybridClient` from `@soulos/sdk` — same methods.

## Hybrid API v0.2

| Step | Endpoint | Notes |
|------|----------|-------|
| Health | `GET /ready` | Use `is_ready()` / graceful fallback |
| Bootstrap | `POST /v1/avatars/ensure` | `external_key` + soul JSON |
| Pre-turn | `POST /hybrid/prepare` | `system_prompt`, `inner_monologue`, memories |
| Post-turn | `POST /hybrid/complete` | Ingest + `reflect_async` → 202 |

Legacy (still supported): separate identity, retrieve, ingest, `POST /state/reflect`.

## Session memory

Pass **`session_id`** on prepare/complete — stored in `episodic_memories.session_id`. Retrieve merges session rows + global memories.

Do **not** rely on `[session:uuid]` text prefixes (deprecated pattern).

## Prompt templates

`runtime_config.hybrid_prompt_template` placeholders: `{name}`, `{role}`, `{description}`, `{inner_monologue}`, `{memories}`.

## Inference modes

| `INFERENCE_MODE` | Behavior |
|------------------|----------|
| `full` | Embeddings + LLM reflect on bridge |
| `embeddings_only` | Embeddings on bridge; reflect without chat model (hybrid apps that own generation) |

## Two databases

Your domain KB stays in **your** Postgres. SoulOS episodic memory lives in the **kernel** Postgres.

## Production

- Kernel private; your API injects [gateway headers](gateway-headers.md) when `REQUIRE_AUTH=1`.
- Preflight: `soulos-doctor --kernel URL --inference URL --embedding-dimension N --bot-id ID`

## Reference

- [examples/hybrid-orchestrator](../../examples/hybrid-orchestrator/)
- [docker-compose.sidecar.yml](../../docker-compose.sidecar.yml)
