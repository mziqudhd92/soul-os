# Deployment

SoulOS supports **dual consumption**: self-host the MIT kernel, or use **SoulOS Cloud** with the same `@soulos/sdk`.

| Mode | Doc | Best for |
|------|-----|----------|
| **Self-hosted** | [self-hosted.md](self-hosted.md) | OSS, privacy, custom models, full kernel |
| **Helm (K8s)** | [deploy/helm/soulos](../../deploy/helm/soulos/) | Minimal chart for kernel + optional gateway |
| **Cloud** | [cloud.md](cloud.md) | Managed API keys, zero-ops inference |
| **Flow authority** | [authority.md](authority.md) | Declare which surface owns the API for agents |

Both paths use the same soul files and SDK methods — only client configuration changes.

**Scale:** [horizontal-scale.md](../guides/horizontal-scale.md) · **OTel:** [observability.md](../guides/observability.md)

**Security:** [SECURITY.md](../../SECURITY.md) — `REQUIRE_AUTH`, gateway exposure, MCP power on `/mcp/*`.
