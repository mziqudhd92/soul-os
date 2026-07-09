# How-to: Session-scoped memory

**Task:** scope episodic memory per user/conversation, and delete it (GDPR / teardown).

**See also:** [Hybrid API](../reference/hybrid-api.md#memory-with-session_id) · [Identity model](identity-model.md) · [API reference](../reference/api.md)

## When to use `session_id`

| Scope | How |
|-------|-----|
| Global (avatar-wide) | Omit `session_id` on ingest / prepare / complete |
| Per conversation / user | Pass the same `session_id` string on prepare, complete, and memory calls |

When `session_id` is set on retrieve/prepare, the kernel merges **global** rows (`session_id IS NULL`) with **session** rows. Ingest tags new facts with that session.

## Hybrid turn with a session

```bash
export KERNEL=http://localhost:8001   # or :8000 full stack
export BOT_ID=<uuid>
export SESSION=user-42:chat-7

curl -s -X POST "$KERNEL/hybrid/prepare" \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT_ID\",\"query\":\"Remember my name is Ada\",\"session_id\":\"$SESSION\"}"

# ... your LLM ...

curl -s -X POST "$KERNEL/hybrid/complete" \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT_ID\",\"summary\":\"User name is Ada\",\"user_message\":\"Remember my name is Ada\",\"session_id\":\"$SESSION\",\"reflect\":false}"
```

List session memories:

```bash
curl -s "$KERNEL/bot/$BOT_ID/memories?session_id=$SESSION"
```

## Delete one session (conversation teardown)

**REST-only** (no MCP tool in v0.2):

```bash
curl -s -X DELETE "$KERNEL/memory/session/$BOT_ID/$SESSION"
# {"status":"success","deleted":N,"bot_id":"...","session_id":"..."}
```

## Forget by content match (GDPR-style scrub)

Deletes rows whose content ILIKE-matches `content_match` for that bot (all sessions unless you filter in app logic first).

```bash
curl -s -X POST "$KERNEL/memory/forget" \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT_ID\",\"content_match\":\"Ada\"}"
# {"status":"success","deleted":N}
```

## Direct memory APIs

```bash
# Ingest with session
curl -s -X POST "$KERNEL/memory/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT_ID\",\"content\":\"Prefers email\",\"session_id\":\"$SESSION\"}"

# Retrieve with session merge
curl -s -X POST "$KERNEL/memory/retrieve" \
  -H "Content-Type: application/json" \
  -d "{\"bot_id\":\"$BOT_ID\",\"query\":\"contact preference\",\"top_k\":5,\"session_id\":\"$SESSION\"}"
```

## Tips

- Use opaque ids (`uuid`, `workspace:user:thread`) — do not put PII in `session_id` itself if logs are retained.
- `runtime_config.memory_policy` is a v0.2 stub (`summary_only` default); document your app’s ingest policy separately.
- MCP tools do **not** expose forget/session delete — use REST ([mcp-tools.md](../reference/mcp-tools.md)).
