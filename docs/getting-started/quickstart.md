# 15-Minute Quickstart: Support Agent vs Dev Twin (Same Runtime)

SoulOS uses one kernel for every avatar type. You only change the **soul file** and **what you ingest**.

## Prerequisites

```bash
docker compose up --build
# Kernel: http://localhost:8000
```

<a id="path-a"></a>

## Path A — Support agent (5 minutes)

```bash
# 1. Register soul
curl -X POST http://localhost:8000/v1/avatars \
  -H "Content-Type: application/json" \
  -d @examples/support-bot/support-bot.soul.json

# 2. Ingest FAQ
curl -X POST http://localhost:8000/memory/ingest \
  -H "Content-Type: application/json" \
  -d '{"bot_id":"<id>","content":"Full refunds within 30 days of purchase."}'

# 3. Chat
curl -N -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d '{"bot_id":"<id>","message":"Can I get a refund after 20 days?"}'
```

## Path B — Dev twin (5 minutes)

```bash
curl -X POST http://localhost:8000/v1/avatars -d @examples/dev-twin/dev-twin.soul.json

curl -X POST http://localhost:8000/memory/ingest \
  -d '{"bot_id":"<id>","content":"POST /v1/avatars registers avatars with validated HEXACO MSV."}'

curl -N -X POST http://localhost:8000/chat/generate \
  -d '{"bot_id":"<id>","message":"How do I register a new avatar?"}'
```

## TypeScript SDK (same runtime)

```typescript
import { SoulOSClient } from '@soulos/sdk';
import { registerAvatarFromFile } from '@soulos/sdk/node';

const soul = new SoulOSClient({ baseUrl: 'http://localhost:8000' });
const { id } = await registerAvatarFromFile(soul, './examples/support-bot/support-bot.soul.json');
await soul.ingestMemory(id, 'Full refunds within 30 days.');

for await (const event of soul.sendMessage(id, 'I need a refund')) {
  if (event.type === 'message') process.stdout.write(event.text);
}
```

## Hosted API (same client)

```typescript
const soul = new SoulOSClient({ apiKey: process.env.SOULOS_API_KEY });
```

Only the config changes — not your application code.

## Soul Studio (optional)

Open [http://localhost:8765](http://localhost:8765) to tune traits, export `.soul.json`, or deploy to the kernel. See [Soul Builder](soul-builder.md).

## MCP (5 minutes)

Connect Cursor to `http://localhost:8000/mcp/sse` — [examples/mcp](../../examples/mcp/README.md) · [MCP guide](../guides/mcp.md).

## Next steps

- [Overview](overview.md) — stack orientation and security notes
- [Python bot integration](../guides/python-bot.md) — wire SoulOS into an existing bot
- [Soul standard](../reference/soul-standard.md) — full `.soul.json` specification
- [API reference](../reference/api.md) — REST + SSE events
- [Deployment](../deployment/README.md) — self-host vs Cloud
