# Multi-agent handoff (Phase B)

Kernel-supported Customer → Inventory handoff with **shared conversation memory**.

`handoff_to` prefers `POST /v1/handoffs` (atomic, idempotent). Older kernels fall back to Phase A (complete + ingest).

## Prerequisites

```bash
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d
# Kernel at http://localhost:8000
```

## Run

```bash
python3 examples/multi-agent-handoff/run_handoff.py --kernel http://localhost:8000
```

The script:

1. Imports `customer-front` and `inventory` SoulPacks (convert-only).
2. Ensures avatars with stable keys `org:{org}:customer` and `org:{org}:inventory`.
3. Prepares on Customer, mock-replies, then `handoff_to` (Phase B handoff API when available).
4. Prepares on Inventory with the same `conv:{conversation_id}` session (shared + bot episodic memories).

## SDK

```python
from soulos import SoulHybridClient, handoff_to, role_external_key, conversation_session_id

session = conversation_session_id("thread-1")
# ... ensure both bots, prepare on current ...
await handoff_to(
    client,
    from_bot_id=customer_id,
    to_bot_id=inventory_id,
    from_role="customer",
    to_role="inventory",
    conversation_id="thread-1",
    reason="stock check",
    summary="User needs SKU-42 overnight",
    idempotency_key="handoff-thread-1-1",
)
```

Guide: [docs/guides/multi-agent-teams.md](../../docs/guides/multi-agent-teams.md)
