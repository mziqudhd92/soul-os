# Ved-travels (sample integration)

This is a **reference example** for applying the hybrid orchestrator pattern to a travel planner:

- **Your app** keeps LiteLLM + tools (`update_preferences`, `search_croatia_knowledge`, affiliate search) and the SSE contract (`thought`, `text`, `tool_call`).
- **SoulOS** owns the assistant’s HEXACO soul (e.g. Vedrana) and episodic memory in pgvector.

## Apply the pattern

1. Read [hybrid orchestrator example](../hybrid-orchestrator/README.md).
2. Copy `../hybrid-orchestrator/soul_client.py` into your Croatia / Ved-travels backend.
3. Run SoulOS on **port 8001** if your backend already uses **8000**.
4. Point `INFERENCE_API_URL` at Ollama or the [inference bridge](../../docs/deployment/inference.md) — not Bedrock/OpenAI `/v1` URLs.

## Architecture (sample)

```
PlannerChat.tsx → your /api/chat/stream
  → soul_client (identity + retrieve + ingest + reflect)
  → LiteLLM + domain tools → your verified_knowledge DB
SoulOS kernel → episodic_memories (separate from your travel KB)
```

Do **not** replace your chat stream with SoulOS `POST /chat/generate` if you rely on custom tools and SSE events.
