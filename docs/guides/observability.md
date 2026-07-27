# Observability (OpenTelemetry)

SoulOS kernel emits **OpenTelemetry** telemetry on the hybrid sidecar path so you can debug prepare/complete latency and memory retrieval in Grafana, Datadog, Phoenix, or Langfuse via OTLP.

## Enable

```bash
# Spans + metrics (OTLP HTTP)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# Or enable without exporting (local TracerProvider / MeterProvider)
export SOULOS_OTEL_ENABLED=1
```

Optional Python extras on the kernel:

```bash
pip install 'soulos-core[otel]'
# or: opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

If OTel packages are missing, telemetry is a **no-op** (kernel still runs).

## What is recorded

| Signal | Name / span | Notes |
|--------|-------------|--------|
| Trace | `soulos.hybrid.prepare` | OpenInference `RETRIEVER`; `bot.id`, `session.id`, memory count |
| Trace | `soulos.hybrid.complete` | OpenInference `CHAIN`; ingest path |
| Metric | `soulos.hybrid.duration` (histogram, seconds) | Attribute `operation=prepare\|complete` |

Token usage is owned by **your** LLM provider — SoulOS does not call the chat model on the hybrid path (`INFERENCE_MODE=embeddings_only` is typical).

## Production tips

- Correlate app request IDs with `bot.id` / `session.id` span attributes.
- Alert on `soulos.hybrid.duration` p95 for prepare (often embed + retrieve bound).
- Studio turn inspector exports prepare JSON/curl for local debugging without OTel.

## Related

- [Hybrid API](../reference/hybrid-api.md#observability-opentelemetry)
- [SignalPR playbook](../playbooks/signalpr-hybrid.md)
- Code: `packages/soulos-core/runtime/telemetry.py`
