# Multi-agent teams (Phase A)

Run specialist avatars as a **team in your app** using today’s SoulOS kernel. There is no teams or handoff API yet — you orchestrate routing, then use `ensure` / `prepare` / `complete` / `memory/ingest`.

**See also:** [Identity model](identity-model.md) · [Hybrid API](../reference/hybrid-api.md) · [SoulPacks](persona-packs.md) · [examples/multi-agent-handoff](../../examples/multi-agent-handoff/)

---

## What Phase A is

| Concern | Who owns it |
|---------|-------------|
| Which specialist speaks | Your conductor (router / LLM tool / rules) |
| Stable identity per role | `external_key` via `POST /v1/avatars/ensure` |
| Conversation correlation | App `conversation_id` → `session_id` `conv:{id}` on each bot |
| Memory | Still **per `bot_id`** — share context by ingesting a handoff note |
| Personality | Separate souls / SoulPacks per role |

Phase B (later) may add kernel teams, shared conversation memory, and capability query. Do not wait on that to ship multi-bot flows.

---

## Conventions

### 1. One avatar per role, stable keys

```text
org:{org_id}:{role}   →   e.g. org:acme:customer , org:acme:inventory
```

Python helper:

```python
from soulos import role_external_key
role_external_key("acme", "customer")  # "org:acme:customer"
```

Bootstrap each specialist once (or on every deploy — `ensure` is idempotent):

```bash
# Import SoulPack souls, then ensure with your keys
curl -X POST http://localhost:8000/v1/avatars/import-soulpack \
  -H "Content-Type: application/json" \
  -d '{"pack_id":"customer-front","persist":false}'
```

Use the returned `soul` with `POST /v1/avatars/ensure` and `external_key: "org:acme:customer"`. Repeat for `inventory`.

First-party packs for this pattern: `customer-front`, `inventory` under `packs/soulpacks/`.

### 2. Shared conversation id (app-level)

Keep one `conversation_id` for the user thread. Map it to the hybrid `session_id`:

```python
from soulos import conversation_session_id
session_id = conversation_session_id("thread-9")  # "conv:thread-9"
```

Pass the **same** `session_id` on prepare/complete for whichever bot is active. That scopes each specialist’s episodic memory for the thread; it does **not** merge memories across bots.

### 3. Handoff recipe

When the conductor switches specialists:

1. **Complete** the current bot (turn summary + optional `user_message`).
2. **Ingest** a handoff note into the **next** bot’s memory (`POST /memory/ingest`, same `session_id`).
3. **Prepare** on the next `bot_id` with the user’s follow-up (or a rewritten specialist query).

SDK helper:

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
    payload={"sku": "SKU-42"},
)
# result["session_id"] == "conv:thread-9"
await client.prepare_turn(
    "Confirm SKU-42 for overnight.",
    bot_id=inventory_bot_id,
    session_id=result["session_id"],
)
```

Handoff notes are plain text starting with `[SoulOS handoff]` so retrieves and prompts can surface them.

---

## Conductor sketch

```text
User message
    → route(role)   # your rules or tool call
    → prepare(bot_id[role], session_id=conv:…)
    → your LLM
    → if tool=handoff(to_role): handoff_to(...) then prepare(next)
    → else complete(current)
```

Capabilities stay app metadata until Phase B: store `capabilities: ["billing","returns"]` next to each `bot_id` in your DB; the kernel does not query them yet.

---

## Demo

```bash
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d
python3 examples/multi-agent-handoff/run_handoff.py
```

---

## Limits (intentional)

- No shared vector memory across bots — only the handoff note (and anything else you ingest).
- No atomic “team turn” — two HTTP steps for transfer.
- Reflection on handoff complete defaults to off in `handoff_to` (`reflect=False`) so transfers stay fast; set `reflect=True` if you want MSV updates on the source bot.
