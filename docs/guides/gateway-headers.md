# Gateway headers (cloud / production sidecars)

When the SoulOS kernel runs with **`REQUIRE_AUTH=1`**, direct public access is rejected. Your **backend (BFF)** calls the kernel on a private network and injects trusted headers.

## Required headers

| Header | Env on kernel | Purpose |
|--------|---------------|---------|
| `X-SoulOS-Gateway-Secret` | `GATEWAY_SECRET` | Shared secret; must match exactly |
| `X-SoulOS-Account-Id` | — | Tenant UUID for multi-tenant isolation |

Both headers are required when `REQUIRE_AUTH=1`. Missing or wrong secret → **401**.

## Optional scopes (gateway-injected)

| Header | Source | Purpose |
|--------|--------|---------|
| `X-SoulOS-Scopes` | API key `scopes` in `keys.json` / `SOULOS_API_KEYS` | Comma-separated privileges (e.g. `mcp:admin:msv_write`) |

**SoulOS Cloud gateway** strips any client-supplied `X-SoulOS-Account-Id`, `X-SoulOS-Gateway-Secret`, and `X-SoulOS-Scopes`, then injects trusted values from the validated API key. Clients cannot forge admin scopes by sending the header themselves.

Self-hosted BFFs that call the kernel directly must inject the same headers and treat them as trusted — do not forward end-user values for these three.

Example key entry:

```json
{
  "sk_live_…": {
    "account_id": "uuid-of-tenant",
    "scopes": ["mcp:admin:msv_write"]
  }
}
```

## Open mode (local dev)

`REQUIRE_AUTH=0` (default in Docker Compose): headers optional. Any client with kernel access can use any `bot_id` — **do not expose port 8000 publicly**. For local admin MCP tools without gateway scopes, set `SOULOS_MCP_ADMIN_TOOLS=1` on the kernel.

## BFF pattern

```text
Browser → Your API (auth) → SoulOS kernel (private)
                ↑ inject gateway headers on every kernel request
```

Your API already authenticates the user; map them to `X-SoulOS-Account-Id` (workspace owner, org id, etc.). Optional: map privileged roles to `X-SoulOS-Scopes`.

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
