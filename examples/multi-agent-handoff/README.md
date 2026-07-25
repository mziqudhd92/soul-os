# Multi-agent handoff (Phase A)

App-orchestrated Customer → Inventory handoff using existing SoulOS hybrid APIs. No kernel `teams` endpoint.

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
3. Prepares on Customer, mock-replies, then `handoff_to` (complete + ingest note).
4. Prepares on Inventory with the same `conv:{conversation_id}` session.

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
    payload={"sku": "SKU-42"},
)
await client.prepare_turn(query, bot_id=inventory_id, session_id=session)
```

See [Multi-agent teams](../../docs/guides/multi-agent-teams.md).
