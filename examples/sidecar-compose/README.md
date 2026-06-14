# Sidecar + your API (compose example)

Wire SoulOS next to your existing backend on a shared Docker network.

## Option A — submodule + sidecar file

```bash
git submodule add https://github.com/mziqudhd92/soul-os.git vendor/soul-os
```

Run soul-os sidecar stack:

```bash
docker compose -f vendor/soul-os/docker-compose.sidecar.yml --profile bridge-mock up -d
```

Your app `.env`:

```bash
SOULOS_KERNEL_URL=http://localhost:8001   # host port from sidecar compose
SOULOS_ENABLED=true
```

## Option B — merge into your `docker-compose.yml`

```yaml
services:
  your-api:
    build: ./core-api
    ports:
      - "7000:8000"
    environment:
      SOULOS_KERNEL_URL: http://soulos-kernel:8000
      SOULOS_ENABLED: "true"
    depends_on:
      - soulos-kernel
    networks:
      - app_net

  soulos-kernel:
    build:
      context: ./vendor/soul-os
      dockerfile: packages/soulos-core/Dockerfile
    ports:
      - "8100:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:changeme_local_dev@soulos-db:5432/senticore
      INFERENCE_API_URL: http://soulos-inference-bridge:11434
      EMBEDDING_DIMENSION: "1024"
      INFERENCE_SKIP_PULL: "1"
    depends_on:
      soulos-db:
        condition: service_healthy
    networks:
      - app_net

  soulos-db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: changeme_local_dev
      POSTGRES_DB: senticore
    networks:
      - app_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      retries: 5

  soulos-inference-bridge:
    profiles: ["bridge-aws", "bridge-mock"]
    build:
      context: ./vendor/soul-os
      dockerfile: packages/soulos-inference-bridge/Dockerfile
    environment:
      BRIDGE_MODE: mock
      EMBEDDING_DIMENSION: "768"
    networks:
      - app_net

networks:
  app_net:
    driver: bridge
```

Start with mock bridge (no AWS):

```bash
docker compose --profile bridge-mock up your-api soulos-kernel soulos-db soulos-inference-bridge
```

## Preflight

```bash
python vendor/soul-os/scripts/soulos-doctor.py \
  --kernel http://localhost:8100 \
  --inference http://localhost:11434 \
  --embedding-dimension 768
```

## Docs

- [Sidecar integration guide](../../docs/guides/sidecar-integration.md)
- [Upstream sidecar compose](../../docker-compose.sidecar.yml)
