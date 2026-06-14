# Hybrid orchestrator

Keep your **existing chat + tools + SSE**; use SoulOS for **soul + episodic memory**.

## Hybrid API v0.2 (sidecar)

| Step | Endpoint | Notes |
|------|----------|-------|
| Health | `GET /ready` | db + inference checks |
| Bootstrap avatar | `POST /v1/avatars/ensure` | `external_key` + soul JSON |
| Pre-turn | `POST /hybrid/prepare` | One call: identity, memories, `system_prompt`, `inner_monologue` |
| Post-turn | `POST /hybrid/complete` | Ingest + `reflect_async` (non-blocking) |

Legacy flow (still supported): separate `GET /bot/{id}/identity`, `POST /memory/retrieve`, ingest, `POST /state/reflect`.

## Session memory

Pass `session_id` on prepare, complete, ingest, and retrieve. Episodic rows are stored with a `session_id` column; retrieve also includes global memories (`session_id` null).

## Prompt templates

Set `runtime_config.hybrid_prompt_template` on the soul (via `POST /v1/avatars` or ensure) with placeholders:

- `{name}`, `{role}`, `{description}`, `{inner_monologue}`, `{memories}`

## Inference modes

| `INFERENCE_MODE` | Behavior |
|------------------|----------|
| `full` (default) | Embeddings + LLM reflect |
| `embeddings_only` | Embeddings only; reflect updates `inner_monologue` without chat model |

## Two databases

Your domain KB stays in **your** Postgres. SoulOS episodic memory lives in the **kernel** Postgres.

## Client

Python: `SoulHybridClient` from `soulos` package — see [examples/hybrid-orchestrator](../../examples/hybrid-orchestrator/).

Sidecar compose: [docker-compose.sidecar.yml](../../docker-compose.sidecar.yml)
