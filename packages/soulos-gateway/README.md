# soulos-gateway

HTTP gateway for **SoulOS Cloud** — validates Bearer API keys, rate limits, proxies REST and MCP SSE to the kernel.

- **Local cloud stack:** `docker compose -f docker-compose.cloud.yml up` from repo root
- **Default port:** 8080
- **Keys:** copy `keys.example.json` → `keys.json` (gitignored) or set `SOULOS_API_KEYS` env
- **Tests:** `pytest` or `npm run test:gateway` from repo root

Docs: [SoulOS Cloud](../../docs/deployment/cloud.md)
