# ClawSouls + SoulOS sidecar

Run SoulOS beside your API and bootstrap a ClawSouls persona on startup.

## Quick start

```bash
# 1. Start kernel + inference (sidecar stack)
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d

# 2. Import Surgical Coder into the kernel
curl -s -X POST http://localhost:8001/v1/avatars/import-clawsouls \
  -H "Content-Type: application/json" \
  -d '{"owner":"clawsouls","name":"surgical-coder","persist":true}'
```

Save the returned `id` as `BOT_ID`. Use hybrid prepare/complete from your app:

```bash
export SOULOS_KERNEL_URL=http://localhost:8001
export BOT_ID=<id from import>
```

Or run the seed script (kernel must be up):

```bash
packages/soulos-core/.venv/bin/python examples/clawsouls-sidecar/seed_clawsoul.py \
  --kernel-url http://localhost:8001 \
  --soul clawsouls/surgical-coder
```

## OpenClaw pattern

1. `npx clawsouls use surgical-coder` in your OpenClaw workspace (tools + SOUL.md).
2. SoulOS sidecar holds **memory + MSV drift** with `external_key: clawsouls:clawsouls/surgical-coder`.
3. Your orchestrator calls `POST /hybrid/prepare` before each LLM call.

See [sidecar integration](../../docs/guides/sidecar-integration.md) and [ClawSouls import](../../docs/guides/clawsouls-import.md).

SoulOS is not affiliated with or endorsed by ClawSouls. Imported persona text remains under each soul's SPDX license.
