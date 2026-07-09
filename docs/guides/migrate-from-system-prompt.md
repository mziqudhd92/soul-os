# How-to: Migrate from a system prompt to a soul

**Task:** you have a large static system prompt — convert it into a SoulOS soul without losing behavior.

**See also:** [Soul standard](../reference/soul-standard.md) · [Psychometrics](psychometrics.md) · [My first sidecar](../tutorials/my-first-sidecar.md)

## Before → after

**Before (fragile):**

```text
You are Acme Support. Be friendly but concise. Never invent policy.
Refunds: 30 days. Escalate billing disputes to humans.
Always admit when you are unsure.
```

**After (soul + memory):**

| Prompt fragment | Goes into |
|-----------------|-----------|
| Role / voice / hard rules | `description` (or Markdown body of `.soul`) |
| Tone knobs (“friendly”, “strict”) | `persona_mode: simple` sliders **or** `baseline_msv.hexaco` |
| Facts / FAQ / policies | Episodic memory (`/memory/ingest` or `.soul-memory/`) — **not** the soul file |

## Minimal soul (simple persona)

No HEXACO literacy required — authoring fields are stripped at registration:

```json
{
  "name": "Acme Support",
  "role": "Customer Support",
  "description": "You are Acme Support. Be friendly but concise. Never invent policy. Escalate billing disputes to humans. Admit when you are unsure.",
  "attachment_style": "Secure",
  "persona_mode": "simple",
  "simple_persona": { "warmth": 0.85, "rigor": 0.8, "caution": 0.75 }
}
```

Register (full stack or sidecar):

```bash
curl -s -X POST http://localhost:8000/v1/avatars/ensure \
  -H "Content-Type: application/json" \
  -d '{"external_key":"acme-support","soul":{...}}'
```

Then ingest policy facts:

```bash
curl -s -X POST http://localhost:8000/memory/ingest \
  -H "Content-Type: application/json" \
  -d '{"bot_id":"<id>","content":"Full refunds within 30 days of purchase."}'
```

## Advanced: map tone words → HEXACO

| Prompt language | Slider / trait |
|-----------------|----------------|
| Warm, empathetic | Warmth ↑ or Agreeableness (A) ↑ |
| Strict, checklist | Rigor ↑ or Conscientiousness (C) ↑ |
| Cautious, no speculation | Caution ↑ / lower epistemic_uncertainty |
| Creative brainstorming | Openness (O) ↑ |

Full table: [psychometrics.md](psychometrics.md).

## Hybrid apps

Keep your LLM call. Replace the static system string with `prepare.system_prompt` each turn:

```text
ensure → prepare → your LLM(system_prompt) → complete
```

Tutorial: [my-first-sidecar.md](../tutorials/my-first-sidecar.md).

## Full-chat apps

If SoulOS should stream replies, use `send_message` / `POST /chat/generate` after register — [python-bot.md](python-bot.md).

## Checklist

1. Split **identity rules** vs **facts**
2. Put rules in `description`; put facts in memory
3. Prefer `persona_mode: simple` for first cut; switch to Advanced HEXACO later in Studio
4. Use `ensure` + `external_key` so deploys are idempotent
5. Verify with a second turn that memory is recalled
