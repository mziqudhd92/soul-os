# Multi-agent teams

Run specialist avatars as a team. **Phase B (shipped in 0.6.0)** adds shared conversation memory, atomic kernel handoffs, and capability query. **Phase A** (app-orchestrated complete + ingest) remains a compatible fallback.

**See also:** [Identity model](identity-model.md) · [Hybrid API](../reference/hybrid-api.md) · [SoulPacks](persona-packs.md) · [examples/multi-agent-handoff](../../examples/multi-agent-handoff/) · [0.6.0 report](../reports/phase-b-ml-improvements.md)

---

## Phase B (recommended)

| Concern | Who owns it |
|---------|-------------|
| Which specialist speaks | Your conductor (router / LLM tool / rules) |
| Stable identity per role | `external_key` via `POST /v1/avatars/ensure` |
| Shared thread memory | `POST /v1/conversations/{id}/memory` (tenant-scoped) |
| Transfer | `POST /v1/handoffs` with `idempotency_key` |
| Capability discovery | `GET /v1/avatars/by-capability/{capability}` |
| Prepare merge | Hybrid prepare merges bot episodic + shared (+ semantic) under budgets when `session_id` is `conv:…` |

```bash
# Shared ingest
curl -X POST http://localhost:8000/v1/conversations/thread-9/memory \
  -H "Content-Type: application/json" \
  -d '{"content":"User prefers overnight shipping","source_bot_id":"<customer_bot>"}'

# Atomic handoff
curl -X POST http://localhost:8000/v1/handoffs \
  -H "Content-Type: application/json" \
  -d '{
    "from_bot_id":"<customer>","to_bot_id":"<inventory>",
    "from_role":"customer","to_role":"inventory",
    "conversation_id":"thread-9","reason":"stock check",
    "summary":"SKU-42 overnight","idempotency_key":"t9-1"
  }'
```

Python SDK `handoff_to(...)` calls `/v1/handoffs` when available.

---

## Phase A (fallback)

App orchestrates: complete current bot → ingest handoff note into next bot → prepare. Same `conversation_session_id` correlates turns; memory stays per `bot_id` unless you also write shared conversation memory.

```python
from soulos import SoulHybridClient, handoff_to, conversation_session_id

client = SoulHybridClient(base_url="http://localhost:8000")
result = await handoff_to(
    client,
    from_bot_id=customer_bot_id,
    to_bot_id=inventory_bot_id,
    from_role="customer",
    to_role="inventory",
    conversation_id="thread-9",
    reason="stock and overnight feasibility",
    summary="User asked for SKU-42 overnight shipping.",
)
await client.prepare_turn(
    "Confirm SKU-42 for overnight.",
    bot_id=inventory_bot_id,
    session_id=result["session_id"],
)
```

---

## Conventions

### One avatar per role

```text
org:{org_id}:{role}   →   e.g. org:acme:customer , org:acme:inventory
```

### Shared conversation id

```python
from soulos import conversation_session_id
session_id = conversation_session_id("thread-9")  # "conv:thread-9"
```

---

## Demo

```bash
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d
python3 examples/multi-agent-handoff/run_handoff.py
```
