# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` branch | Yes |
| Released tags | Best effort |

## Reporting a vulnerability

**Do not** open public GitHub issues for security bugs.

Email or contact the maintainers privately with:

- Description and impact
- Steps to reproduce
- Suggested fix (if any)

We aim to acknowledge reports within a few business days.

## Deployment expectations

- **Self-host (`REQUIRE_AUTH=0`)**: intended for local development only — do not expose the kernel port publicly without gateway auth. MCP endpoints (`/mcp/*`) have the same power as REST (memory ingest, avatar registration, MSV updates).
- **Cloud (`REQUIRE_AUTH=1`)**: expose only `soulos-gateway`; rotate `GATEWAY_SECRET` and API keys in production. MCP is available at `/mcp/sse` through the gateway with Bearer API keys.
- **Soul Studio**: local dev tool; do not expose port 8765 publicly without access control.

See [docs/deployment/self-hosted.md](docs/deployment/self-hosted.md).
