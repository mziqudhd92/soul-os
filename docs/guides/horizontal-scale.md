# Horizontal scale

SoulOS kernel pods can scale horizontally when **avatar and memory state stay in Postgres**. This guide documents what is shared vs process-local.

## Safe to scale (DB-backed)

- Bot identity / MSV (`bots` table)
- Episodic memory (`episodic_memories` + pgvector)
- `ensure` by `external_key` (unique per tenant)

Any kernel replica can serve `prepare` / `complete` for the same `bot_id`.

## Process-local caveats

| Component | Behavior | Multi-replica guidance |
|-----------|----------|------------------------|
| Async MSV reflect (`reflect_async=true`) | `BackgroundTasks` on the pod that accepted `complete` | Prefer `reflect_async=false` under HPA, or accept best-effort reflect on that pod only |
| Gateway rate limiter (default) | **In-memory** sliding window | Run **one** gateway replica, or set `REDIS_URL` for shared limits |
| Gateway rate limiter (Redis) | Minute buckets in Redis | Required for multi-replica Cloud gateway |

```bash
# Shared rate limits across gateway pods
export REDIS_URL=redis://redis:6379/0
```

## Kubernetes

- Probe kernel with `GET /ready` (not only `/health`).
- Use the Helm chart under [`deploy/helm/soulos`](../../deploy/helm/soulos/) for a starter Deployment + Service + Postgres values.
- Autoscale on CPU/RPS; memory pressure often tracks embed concurrency.

## Session memory TTL

Set `MEMORY_SESSION_TTL_SECONDS` so session-scoped rows age out of retrieve and can be purged:

```bash
export MEMORY_SESSION_TTL_SECONDS=86400   # 24h
# One bot:
curl -X POST http://localhost:8000/memory/purge-expired -H 'content-type: application/json' -d '{"bot_id":"<uuid>"}'
# All bots (operator / CronJob; auth off or no tenant account):
curl -X POST http://localhost:8000/memory/purge-expired -H 'content-type: application/json' -d '{}'
```

Helm: set `purgeCron.enabled=true` when TTL &gt; 0 (see `deploy/helm/soulos`).

Global memories (`session_id` null) are **not** expired by this TTL. See [session-memory.md](session-memory.md).

## Non-goals

Kafka/Redis PubSub event mesh and sticky sessions are not required for hybrid sidecar. See [non-goals.md](../design/non-goals.md).
