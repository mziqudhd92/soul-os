# SoulPack sidecar seed

Seed a first-party MIT [SoulPack](../../docs/guides/persona-packs.md) into a running kernel, then use the hybrid sidecar path.

```bash
# Kernel + mock bridge
docker compose -f docker-compose.sidecar.yml --profile bridge-mock up -d

# Convert-only (no DB write)
python3 examples/soulpack-sidecar/seed_soulpack.py --pack-id support-agent --persist false

# Ensure avatar in kernel
python3 examples/soulpack-sidecar/seed_soulpack.py --pack-id companion --persist true \
  --kernel http://localhost:8000
```

Then continue with `npm run smoke:hybrid` or your app’s `prepare → LLM → complete` loop.
