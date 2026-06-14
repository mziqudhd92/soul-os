# Soul Builder (local UI)

Configure a validated soul in your browser — **`.soul`** (YAML + Markdown) or legacy **`.soul.json`** — no hand-editing required.

Python + JSON. No Node.js build step.

## Quick start

```bash
git clone https://github.com/mziqudhd92/soul-os.git soulos
cd soulos
docker compose up --build
```

Open **http://localhost:8765**

| Step | Action |
|------|--------|
| 1 | Set **name**, **role**, **description**, attachment style |
| 2 | Tune **HEXACO**, moral foundations, and drives |
| 3 | **Export JSON** or **Export .soul** → downloads soul file |
| 4 | (Optional) **Deploy to kernel** → register with kernel and test in chat (watch **cognitive_state** rails) |
| 5 | (Optional) **Import** → load `.soul`, `.soul.json`, or JSON from disk |

Same one-liner from npm:

```bash
npm run up
```

## Pip install (no Docker for the UI)

```bash
pip install -e packages/soulos-studio
soulos-studio
# http://127.0.0.1:8765
```

With kernel for deploy + chat:

```bash
docker compose up soulos-kernel db ollama
soulos-studio --kernel http://localhost:8000
```

## What you get

The exported file matches `spec/soul.schema.json` and works with:

- `POST /v1/avatars` (curl or SDK)
- [Python bot tutorial](../guides/python-bot.md)
- `examples/*` workflows

## Import / export

- **Import** — `.soul`, `.soul.json`, or JSON from disk (e.g. `examples/support-bot/support-bot.soul`)
- **Export JSON** / **Export .soul** — current form state
- **Deploy to kernel** — `POST /v1/avatars` (requires kernel on :8000); chat panel shows dual-process rails on `cognitive_state` SSE

You can **export without deploying** — useful when building a soul for a Python bot on another machine.

## See also

- [Psychometric cheat sheet](../guides/psychometrics.md) — what sliders mean
- [Soul standard](../reference/soul-standard.md) — field reference
- [MCP guide](../guides/mcp.md) — use the same avatar from Cursor (`/mcp/sse`)
- [Python bot tutorial](../guides/python-bot.md) — integrate exported souls into your bot
- [Package README](../../packages/soulos-studio/README.md) — CLI flags and pip install
