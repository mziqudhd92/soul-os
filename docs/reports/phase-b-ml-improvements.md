# Phase B + ML quality improvements (0.6.0)

Implementation report for the hybrid retrieval, MSV, eval, consolidation, dual-process, and Phase B shared-memory work.

## Before → after

| Area | Before | After |
|------|--------|--------|
| Retrieval | Dense L2 top-k only | Dense + FTS → cutoff → RRF → importance → capped cosine MMR |
| MSV reflect | Unconstrained LLM JSON write | Clamp, EMA + confidence gate, uncertainty hysteresis |
| Hybrid prompt | name/role/description/monologue | + closed-enum trait directives |
| Dual-process | Always run S2 (telemetry only) | Feature router gates S2; `reflect_force` bypass |
| Multi-agent | Phase A app handoff notes only | Shared `conversation_memories` + `POST /v1/handoffs` |
| Eval | Prompt-string smoke stub | Deterministic retrieval/persona/drift in CI |

## APIs

- `POST /memory/retrieve` — optional `include_scores`
- `POST /memory/consolidate`
- `POST /v1/conversations/{conversation_id}/memory` (+ `/retrieve`)
- `POST /v1/handoffs` — `idempotency_key`
- `GET /v1/avatars/by-capability/{capability}`
- Hybrid prepare: auto-merges shared memory for `conv:` sessions; memory budgets

## Env defaults

See `.env.example`: `MEMORY_RETRIEVAL_MODE`, `MEMORY_MAX_DISTANCE`, `MEMORY_MMR_*`, `MSV_*`, `DEFAULT_UNCERTAINTY_TRIGGER`, `SOULOS_ROUTER_LOG_PATH`, `MEMORY_BUDGET_*`.

## Tests

```bash
npm run test:kernel
npm run test:eval
```

## Hardening (review items)

All 20 review items from the plan are reflected: safe FTS, score-space order, MMR cap, closed traits, EMA gate, hysteresis, deterministic eval + fixture versioning, consolidate locking + provenance, importance×RRF, async router log, S2 fallback metadata, tenant thresholds, tenant shared memory, idempotent handoffs, capability cache, prepare budgets, concurrent FTS indexes, `MemoryHit` scores.
