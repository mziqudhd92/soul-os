# SignalPR hybrid sidebook

Generic playbook for AI-native apps that keep **Bedrock (or other) generation** and use SoulOS as a **hybrid sidecar** — based on [SignalPR](https://signalpr.pro/) production patterns.

## Architecture

1. SignalPR API receives user message
2. `POST /v1/avatars/ensure` with `external_key` per workspace/user
3. `POST /hybrid/prepare` → `system_prompt` + memories
4. Bedrock stream with returned prompt
5. `POST /hybrid/complete` with summary + `reflect_async=true`

## Configuration

```bash
INFERENCE_MODE=embeddings_only
EMBEDDING_DIMENSION=768
INFERENCE_API_URL=http://soulos-inference-bridge:11434
```

## Identity keys

Use stable keys like `signalpr:workspace:{id}:agent:pr` so deploys are idempotent.

## Observability

Enable OTel on kernel (`OTEL_EXPORTER_OTLP_ENDPOINT`) and correlate spans with app request IDs.

## Related docs

- [Sidecar integration](../guides/sidecar-integration.md)
- [Hybrid API](../reference/hybrid-api.md)
- [Identity model](../guides/identity-model.md)
- [examples/fastapi-hybrid/](../../examples/fastapi-hybrid/)
