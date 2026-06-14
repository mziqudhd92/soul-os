# Hybrid orchestrator pattern

Use SoulOS for **persistent soul + episodic memory** while your app keeps **LiteLLM / OpenAI tools + custom SSE**.

## When to use

- You already have `/api/chat/stream` with tool calling and GenUI events.
- You need TripState / domain tools SoulOS does not provide.
- You want HEXACO MSV and pgvector recall without replacing your chat stack.

## Quick start

1. Run SoulOS kernel (and inference plug-in — see [inference guide](../../docs/deployment/inference.md)):

```bash
docker compose --profile ollama up soulos-kernel db
# or: docker compose --profile bridge-mock up soulos-kernel db soulos-inference-bridge
```

2. Register an avatar and copy `bot_id`:

```bash
curl -s -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @../support-bot/support-bot.soul.json
```

3. Copy `soul_client.py` into your backend and wire your stream handler:

```python
from soul_client import SoulClient

soul = SoulClient(base_url="http://localhost:8001")  # use :8001 if your app uses :8000

async def handle_chat(bot_id, session_id, user_message):
    ctx = await soul.get_context(bot_id, user_message)
    system_prompt = soul.build_system_prompt(ctx)
    # Pass system_prompt to your LiteLLM / OpenAI client + your tools
    # ... stream SSE to your UI ...
    await soul.persist_turn(bot_id, session_id, f"User: {user_message}")
    await soul.reflect(bot_id, user_message)
```

4. Preflight:

```bash
python ../../scripts/soulos-doctor.py --kernel http://localhost:8000 --inference http://localhost:11434
```

## Docs

- [Plug in SoulOS](../../docs/guides/plug-in-soulos.md)
- [Hybrid orchestrator guide](../../docs/guides/hybrid-orchestrator.md)

## Example projects

- [Ved-travels sample](../ved-travels/README.md) — travel planner with LiteLLM tools
