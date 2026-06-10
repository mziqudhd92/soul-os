# Companion Example

Personal companion avatar with sample conversation history in [sample-history.json](sample-history.json).

**Prerequisites:** kernel on `http://localhost:8000` — `docker compose up --build` ([Quickstart](../../docs/getting-started/quickstart.md)).

```bash
curl -X POST http://localhost:8000/v1/avatars -d @companion.soul.json

# Ingest prior conversation snippets from sample-history.json
curl -X POST http://localhost:8000/memory/ingest \
  -d '{"bot_id":"<id>","content":"User had a rough day; manager criticized their presentation."}'
```

**See also:** [Psychometrics cheat sheet](../../docs/guides/psychometrics.md) · [Soul Builder](../../docs/getting-started/soul-builder.md)
