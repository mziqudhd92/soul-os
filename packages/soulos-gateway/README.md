# soulos-gateway

HTTP gateway for **SoulOS Cloud** — validates Bearer API keys, rate limits, proxies REST and MCP SSE to the kernel.

- **Local cloud stack:** `docker compose -f docker-compose.cloud.yml up` from repo root
- **Default port:** 8080
- **Keys:** copy `keys.example.json` → `keys.json` (gitignored) or set `SOULOS_API_KEYS` env. Keys may be stored as plaintext (hashed in-memory on load) or as `sha256:<hex>` of the bearer token.
- **Rate limits:** in-memory by default (single replica). Set `REDIS_URL` for shared sliding-window limits across gateway pods. With `GATEWAY_REPLICAS>1`, Redis outages **fail closed** (deny) instead of multiplying per-process limits.
- **Tests:** `pytest` or `npm run test:gateway` from repo root

Docs: [SoulOS Cloud](../../docs/deployment/cloud.md) · [Horizontal scale](../../docs/guides/horizontal-scale.md)
