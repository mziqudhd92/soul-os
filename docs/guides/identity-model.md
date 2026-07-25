# SoulOS identity model

How tenants, avatars, sessions, and memory scopes relate in hybrid sidecar integrations.

**See also:** [Sidecar integration](sidecar-integration.md) · [Hybrid API](../reference/hybrid-api.md) · [Plug in SoulOS](plug-in-soulos.md)

---

## Concepts

| Term | Meaning |
|------|---------|
| **owner_id / account_id** | Tenant scope when `REQUIRE_AUTH=1` and gateway headers are present. Bots belong to one owner. |
| **external_key** | Your stable idempotency key (e.g. `workspace:abc`, `user:123:planner`). Maps to one `bot_id`. |
| **bot_id** | UUID returned by `POST /v1/avatars` or `POST /v1/avatars/ensure`. Used in hybrid and memory calls. |
| **session_id** | Optional conversation scope for episodic memory. When set, retrieve prefers global + session memories; ingest tags new facts. |
| **MSV** | Moral State Vector — HEXACO personality state in `current_msv`, updated by System 2 reflection on `/hybrid/complete`. |

---

## ensure vs register

| Endpoint | When to use |
|----------|-------------|
| `POST /v1/avatars/ensure` | **Production sidecar** — idempotent bootstrap per `external_key`. Safe on every app start. |
| `POST /v1/avatars` | One-shot registration; duplicate souls create new rows unless you manage keys yourself. |

```bash
curl -X POST http://localhost:8000/v1/avatars/ensure \
  -H "Content-Type: application/json" \
  -d '{"external_key":"my-app:user-42","soul":{...}}'
```

---

## Hybrid turn flow

```text
ensure_avatar → POST /hybrid/prepare → your LLM → POST /hybrid/complete
```

1. **prepare** — embed query, retrieve memories, build `system_prompt` + `inner_monologue`.
2. **Your LLM** — stream or batch with the returned prompt (Bedrock, OpenAI, LiteLLM, etc.).
3. **complete** — ingest turn summary into memory; optional async MSV reflection.

Set `INFERENCE_MODE=embeddings_only` when the kernel should never call chat models (sidecar-only).

---

## Session vs global memory

| `session_id` on prepare/complete | Behavior |
|----------------------------------|----------|
| **Set** | Retrieve merges global (`session_id IS NULL`) + session-scoped memories. Ingest tags the new fact with that session. |
| **Omitted** | Global memory only — facts visible across all sessions for that bot. |

Delete session-scoped facts:

```bash
curl -X DELETE "http://localhost:8000/memory/session/<BOT_ID>/<SESSION_ID>"
```

Forget by content match:

```bash
curl -X POST http://localhost:8000/memory/forget \
  -H "Content-Type: application/json" \
  -d '{"bot_id":"<BOT_ID>","content_match":"refund"}'
```

---

## MSV lifecycle

1. **Registration** — `baseline_msv` copied from soul file; `current_msv` starts equal.
2. **Reflection** — `/hybrid/complete` with `user_message` + `reflect=true` runs System 2; updates `current_msv`.
3. **Next prepare** — `system_prompt` uses latest `current_msv` and `inner_monologue`.

Studio and MCP can also read/update identity; hybrid sidecar is the production path for apps that keep their own LLM.

---

## Multi-agent teams (Phase A)

One turn still uses one `bot_id`. For specialist handoffs (e.g. Customer → Inventory):

- Stable keys per role: `org:{org_id}:{role}`
- Shared app `conversation_id` → hybrid `session_id` `conv:{id}` (memory remains per bot)
- On transfer: complete current bot → ingest handoff note on next bot → prepare on next `bot_id`

Full recipe: [Multi-agent teams](multi-agent-teams.md) · [examples/multi-agent-handoff](../../examples/multi-agent-handoff/)

---

## Multi-tenant cloud

When using SoulOS Cloud gateway, pass:

- `X-SoulOS-Gateway-Secret` — shared secret
- `X-SoulOS-Account-Id` — tenant id

`verify_bot_access` ensures `bot_id` belongs to the account. Errors return RFC 7807 Problem Details with `code: ACCESS_DENIED` or `BOT_NOT_FOUND`.
