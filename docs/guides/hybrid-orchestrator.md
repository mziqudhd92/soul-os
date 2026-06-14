# Hybrid orchestrator

Keep your **existing chat + tools + SSE**; use SoulOS for **soul + episodic memory**.

## Pattern

1. `GET /bot/{id}/identity` — persona + `current_msv`
2. `POST /memory/retrieve` — RAG context for the user message
3. Build system prompt (see `examples/hybrid-orchestrator/soul_client.py`)
4. Your LiteLLM / OpenAI client streams with **your tools**
5. `POST /memory/ingest` — persist turn summary
6. `POST /state/reflect` — update HEXACO MSV after the turn

## APIs

| Endpoint | Payload | Response |
|----------|---------|----------|
| `GET /bot/{bot_id}/identity` | — | name, role, description, current_msv |
| `POST /memory/retrieve` | bot_id, query, top_k? | memories[] |
| `POST /memory/ingest` | bot_id, content | status |
| `POST /state/reflect` | bot_id, message | current_msv |

## Session memory

Episodic rows are keyed by `bot_id`. For per-session isolation prefix content:

```text
[session:<uuid>] User asked about pricing for the enterprise plan
```

Or use one `bot_id` per user.

## Two databases

Your domain KB (e.g. product catalog, verified facts) stays in **your** Postgres. SoulOS episodic memory lives in the **kernel** Postgres. Only your app's tools query your KB.

## Inference

Your app's LLM can call Bedrock/GCP/OpenAI directly. SoulOS kernel still needs an inference plug-in for **embeddings** (and reflect). See [inference.md](../deployment/inference.md).

## Reference

- [examples/hybrid-orchestrator](../../examples/hybrid-orchestrator/) — copy `soul_client.py` into your backend
