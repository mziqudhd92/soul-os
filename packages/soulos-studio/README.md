# SoulOS Studio

Pip-installable soul builder — configure HEXACO MSV traits, export validated `.soul.json`, deploy to the kernel, and test chat in your browser.

No Node.js or React. Python + JSON + vanilla HTML/CSS/JS.

## Install

```bash
pip install -e packages/soulos-studio
# or from repo root after clone:
pip install -e ./packages/soulos-studio
```

## Run

```bash
# Soul editing works without a kernel (export / import / validate)
soulos-studio

# Open http://127.0.0.1:8765
```

With kernel for deploy + chat:

```bash
docker compose up soulos-kernel db ollama
soulos-studio --kernel http://localhost:8000
```

Environment: `SOULOS_KERNEL_URL` (default `http://localhost:8000`).

## Docker

```bash
docker compose up --build
# Studio at http://localhost:8765
```

## CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Bind host |
| `--port` | `8765` | Bind port |
| `--kernel` | `$SOULOS_KERNEL_URL` | Kernel URL for deploy & chat |

## Documentation

- [Soul Builder guide](../../docs/getting-started/soul-builder.md)
- [Psychometrics cheat sheet](../../docs/guides/psychometrics.md)
- [MCP guide](../../docs/guides/mcp.md) — kernel tools at `/mcp/sse`
- [Self-hosted deployment](../../docs/deployment/self-hosted.md) — ports and `REQUIRE_AUTH`

## Tests

```bash
npm run test:studio
# or: cd packages/soulos-studio && pip install -e ".[dev]" && pytest -q
```
