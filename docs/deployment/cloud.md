# SoulOS Cloud

Part of [Deployment overview](README.md). For local Docker kernel, see [Self-hosted](self-hosted.md).

Managed API — same `@soulos/sdk` surface as self-host, with API keys and tenant isolation.

## Architecture

```
Client (@soulos/sdk + apiKey)
    → soulos-gateway (:8080)   Bearer sk_… → account_id
    → soulos-kernel (:8000)    REQUIRE_AUTH=1, owner_id scoping
    → Postgres + inference
```

The kernel is **not** exposed publicly in Cloud mode. Only the gateway accepts traffic.

## Local Cloud stack

```bash
docker compose -f docker-compose.cloud.yml up --build
```

Demo API key (from `packages/soulos-gateway/keys.example.json`):

```
sk_test_demo_key_for_local_dev
```

```typescript
import { SoulOSClient } from '@soulos/sdk';

const soul = new SoulOSClient({
  apiKey: 'sk_test_demo_key_for_local_dev',
  baseUrl: 'http://localhost:8080',
});

const { id } = await soul.registerAvatar({
  name: 'Support Bot',
  role: 'Support',
  description: 'Handles refunds',
  attachment_style: 'Secure',
  baseline_msv: { /* see examples/support-bot */ },
});
```

Production SDK (no `baseUrl`):

```typescript
const soul = new SoulOSClient({ apiKey: process.env.SOULOS_API_KEY });
// → https://api.soulos.dev
```

## Configuration

### Gateway (`packages/soulos-gateway`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `KERNEL_URL` | `http://soulos-kernel:8000` | Upstream kernel |
| `GATEWAY_SECRET` | `changeme_gateway_secret` | Shared secret with kernel |
| `SOULOS_KEYS_FILE` | `keys.json` | API key → account map |
| `SOULOS_API_KEYS` | — | JSON override (env) |
| `DEFAULT_RATE_LIMIT_PER_MINUTE` | `120` | Per-key limit |

Key file format:

```json
{
  "sk_live_…": {
    "account_id": "uuid-of-tenant",
    "tier": "cloud",
    "rate_limit_per_minute": 120
  }
}
```

### Kernel (Cloud mode)

| Variable | Default | Purpose |
|----------|---------|---------|
| `REQUIRE_AUTH` | `0` | Set `1` in Cloud — reject direct access |
| `GATEWAY_SECRET` | must match gateway | Validates `X-SoulOS-Gateway-Secret` |

Headers injected by gateway (do not set from clients):

- `X-SoulOS-Account-Id` — tenant UUID
- `X-SoulOS-Gateway-Secret` — internal auth

## Tenant isolation

- `POST /v1/avatars` sets `bots.owner_id` from account id
- All bot-scoped routes verify `owner_id` before memory/chat/state access
- Self-host (`REQUIRE_AUTH=0`) keeps backward compatibility: no account header → no scoping

## Billing (next steps)

This release ships **keys + rate limits**. Stripe Checkout and usage metering can attach to the gateway without kernel changes.

## MCP through the gateway

Cursor and Claude connect to SoulOS MCP over HTTP SSE. In Cloud mode, use the **gateway** URL with your API key — never expose the kernel directly.

```json
{
  "mcpServers": {
    "soulos": {
      "url": "http://localhost:8080/mcp/sse",
      "headers": {
        "Authorization": "Bearer sk_test_demo_key_for_local_dev"
      }
    }
  }
}
```

Production (no local gateway):

```text
https://api.soulos.dev/mcp/sse
```

Same Bearer key as the TypeScript SDK. MCP tools (`ingest_memory`, `retrieve_memory`, `register_avatar`, etc.) are tenant-scoped via the gateway account header. See [MCP guide](../guides/mcp.md) and [examples/mcp](../../examples/mcp/README.md).

## Security

- Rotate `GATEWAY_SECRET` in production
- Do not expose kernel port 8000 on public networks when `REQUIRE_AUTH=1`
- Issue per-customer API keys; map to unique `account_id` UUIDs
- MCP endpoints have the same privileges as REST — protect gateway keys accordingly
