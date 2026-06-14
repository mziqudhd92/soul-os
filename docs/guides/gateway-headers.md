# Gateway headers (cloud / production sidecars)

When the SoulOS kernel runs with **`REQUIRE_AUTH=1`**, direct public access is rejected. Your **backend (BFF)** calls the kernel on a private network and injects trusted headers.

## Required headers

| Header | Env on kernel | Purpose |
|--------|---------------|---------|
| `X-SoulOS-Gateway-Secret` | `GATEWAY_SECRET` | Shared secret; must match exactly |
| `X-SoulOS-Account-Id` | — | Tenant UUID for multi-tenant isolation |

Both headers are required when `REQUIRE_AUTH=1`. Missing or wrong secret → **401**.

## Open mode (local dev)

`REQUIRE_AUTH=0` (default in Docker Compose): headers optional. Any client with kernel access can use any `bot_id` — **do not expose port 8000 publicly**.

## BFF pattern

```text
Browser → Your API (auth) → SoulOS kernel (private)
                ↑ inject gateway headers on every kernel request
```

Your API already authenticates the user; map them to `X-SoulOS-Account-Id` (workspace owner, org id, etc.).

## Python (`SoulHybridClient`)

```python
from soulos import SoulHybridClient

soul = SoulHybridClient(
    base_url="http://soulos-kernel:8000",
    gateway_secret=os.environ["SOULOS_GATEWAY_SECRET"],
    account_id=str(workspace.owner_id),
)
```

## TypeScript (`SoulHybridClient`)

```typescript
const soul = new SoulHybridClient({
  baseUrl: process.env.SOULOS_KERNEL_URL,
  gatewaySecret: process.env.SOULOS_GATEWAY_SECRET,
  accountId: workspace.ownerId,
});
```

## Related

- [Self-hosted deployment](../deployment/self-hosted.md) — `REQUIRE_AUTH`, `GATEWAY_SECRET`
- [SoulOS Cloud](../deployment/cloud.md) — managed gateway
- [Sidecar integration](sidecar-integration.md)
