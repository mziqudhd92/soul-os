# Deployment

SoulOS supports **dual consumption**: self-host the MIT kernel, or use **SoulOS Cloud** with the same `@soulos/sdk`.

| Mode | Doc | Best for |
|------|-----|----------|
| **Self-hosted** | [self-hosted.md](self-hosted.md) | OSS, privacy, custom models, full kernel |
| **Cloud** | [cloud.md](cloud.md) | Managed API keys, zero-ops inference |

Both paths use the same soul files and SDK methods — only client configuration changes.

**Security:** [SECURITY.md](../../SECURITY.md) — `REQUIRE_AUTH`, gateway exposure, MCP power on `/mcp/*`.
