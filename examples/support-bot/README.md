# Support Bot Example

Customer-support avatar with bundled [faq.md](faq.md).

**Prerequisites:** kernel on `http://localhost:8000` — `docker compose up --build` ([Quickstart](../../docs/getting-started/quickstart.md)).

```bash
curl -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @support-bot.soul.json

# Ingest FAQ chunks
curl -X POST http://localhost:8000/memory/ingest \
  -d '{"bot_id":"<id>","content":"Full refunds within 30 days."}'
```

**See also:** [Soul standard](../../docs/reference/soul-standard.md) · [Python bot guide](../../docs/guides/python-bot.md)
