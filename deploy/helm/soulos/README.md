# Helm chart (SoulOS)

Minimal Kubernetes starter for self-hosting the SoulOS kernel + Postgres.

## Install

```bash
# From repo root — adjust image tags for your registry
helm upgrade --install soulos deploy/helm/soulos \
  --namespace soulos --create-namespace \
  --set kernel.image.repository=ghcr.io/example/soulos-kernel \
  --set kernel.image.tag=0.3.0
```

## Values of interest

| Key | Purpose |
|-----|---------|
| `kernel.env.REQUIRE_AUTH` | `0` local / `1` behind gateway |
| `kernel.env.GATEWAY_SECRET` | Shared secret with gateway |
| `kernel.env.OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector |
| `kernel.env.MEMORY_SESSION_TTL_SECONDS` | Session memory TTL (0 = off) |
| `gateway.enabled` | Deploy cloud gateway |
| `gateway.env.REDIS_URL` | Shared rate limits (multi-replica) |
| `postgresql.enabled` | Chart-bundled Postgres (dev only) |

Production: point `DATABASE_URL` at a managed Postgres with `pgvector`, disable bundled DB, and terminate TLS at your ingress.

See [horizontal-scale.md](../../docs/guides/horizontal-scale.md) and [self-hosted.md](../../docs/deployment/self-hosted.md).
