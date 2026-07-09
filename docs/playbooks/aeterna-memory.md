# Aeterna memory playbook

Generic playbook for **long-horizon episodic memory** and stable narrator persona — based on [Aeterna](https://helloaeterna.com/) integration patterns.

## Goals

- Persistent narrator tone (HEXACO MSV) across months of interviews
- Session-scoped facts for family Q&A without cross-family leakage
- Optional global facts (policies, biography themes) visible in all sessions

## Session model

```bash
# Scoped to interview session
curl -X POST http://localhost:8000/hybrid/prepare \
  -d '{"bot_id":"<id>","query":"What did I say about my childhood?","session_id":"family-smith-2026"}'

# Complete ingests into same session
curl -X POST http://localhost:8000/hybrid/complete \
  -d '{"bot_id":"<id>","summary":"...","session_id":"family-smith-2026","user_message":"..."}'
```

When `session_id` is set, retrieve merges **global** (`session_id IS NULL`) + **session** memories.

## Forgetting

```bash
# Delete all memories for a session (GDPR-style)
curl -X DELETE "http://localhost:8000/memory/session/<BOT_ID>/family-smith-2026"

# Forget by content match
curl -X POST http://localhost:8000/memory/forget \
  -d '{"bot_id":"<id>","content_match":"childhood anecdote"}'
```

## Persona

Use `persona_mode: simple` for non-HEXACO operators, or a curated `.soul` for narrator voice. MSV reflection on complete keeps tone consistent without rewriting the soul file each session.

## Related docs

- [Psychometrics guide](../guides/psychometrics.md)
- [Identity model](../guides/identity-model.md)
- [Python bot integration](../guides/python-bot.md)
