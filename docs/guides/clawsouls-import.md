# Import ClawSouls personas

[ClawSouls](https://clawsouls.ai) ships **markdown persona packages** (Soul Spec). SoulOS adds **HEXACO MSV**, episodic memory, dual-process telemetry, and hybrid sidecar APIs. This guide covers conversion and registration.

## When to use

| You have | Use |
|----------|-----|
| OpenClaw / Cursor with `SOUL.md` | Keep ClawSouls for workspace files; add SoulOS for memory + MSV |
| Bedrock/OpenAI app | SoulOS sidecar + `import-clawsouls` + hybrid API |
| Soul Studio | **ClawSouls** tab → Open in Studio or Deploy |

## One-command import (kernel)

```bash
curl -s -X POST http://localhost:8000/v1/avatars/import-clawsouls \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "clawsouls",
    "name": "surgical-coder",
    "persist": true
  }'
```

Response includes `id`, `warnings` (MSV preset notes), and `external_key` (e.g. `clawsouls:clawsouls/surgical-coder@1.3.0`).

### Convert only (no database row)

```bash
curl -s -X POST http://localhost:8000/v1/avatars/import-clawsouls \
  -H "Content-Type: application/json" \
  -d '{"owner":"clawsouls","name":"minimalist","persist":false}'
```

Returns `{ "soul", "runtime_config", "warnings", "external_key" }`.

### Request fields

| Field | Description |
|-------|-------------|
| `owner` | ClawSouls namespace (e.g. `clawsouls`) |
| `name` | Soul slug (e.g. `surgical-coder`) |
| `version` | Optional version pin for `external_key` |
| `external_key` | Override idempotent key (default `clawsouls:{owner}/{name}@{version}`) |
| `msv_preset` | Override MSV preset (`surgical-coder`, `minimalist`, …) |
| `persist` | `true` → `ensure_avatar`; `false` → convert only (`register` alias accepted) |
| `runtime_config` | Merged into stored runtime config |

Disable remote import: `CLAWSOULS_IMPORT_ENABLED=0` on the kernel.

## CLI converter

```bash
# From registry (needs network)
packages/soulos-core/.venv/bin/python scripts/clawsouls_to_soul.py \
  clawsouls/surgical-coder -o my-bot.soul.json

# From local ClawSouls package directory
packages/soulos-core/.venv/bin/python scripts/clawsouls_to_soul.py \
  --dir ~/.openclaw/souls/clawsouls/surgical-coder -o my-bot.soul.json

# Register with running kernel
packages/soulos-core/.venv/bin/python scripts/clawsouls_to_soul.py \
  clawsouls/devops-veteran --register --kernel-url http://localhost:8000
```

## MSV presets

ClawSouls prose does not include HEXACO weights. SoulOS applies curated presets from `packages/soulos-core/runtime/clawsouls_presets.yaml`:

| Preset | Persona vibe |
|--------|----------------|
| `surgical-coder` | High C, low E, minimal diff |
| `minimalist` | Ultra-short, high autonomy |
| `devops-veteran` | Infra opinions, high C |
| `debug-detective` | High curiosity, analytical |
| `personal-assistant` | Warm, high agreeableness |
| `code-reviewer` | Strict, high fairness |
| `gamedev-mentor` | Encouraging, high openness |
| `brad` | Formal eng partner |
| `default` | Neutral Secure baseline |

Warnings in the import response tell you which preset was applied. Tune in Soul Studio after import.

## Soul Studio

1. Open http://localhost:8765 → **ClawSouls**.
2. Search or browse (proxies `clawsouls.ai/api/v1/souls`).
3. **Open in Studio** — loads form + MSV sliders (kernel required).
4. **Deploy to kernel** — registers avatar for chat/MCP.

## Hybrid sidecar + OpenClaw

```text
OpenClaw workspace (SOUL.md, tools)
        ↓
Your app: hybrid/prepare → your LLM → hybrid/complete
        ↓
SoulOS kernel (memory, MSV, external_key: clawsouls:…)
```

Example stack: [examples/clawsouls-sidecar](../examples/clawsouls-sidecar/README.md).

## Dual MCP (Cursor)

```json
{
  "mcpServers": {
    "soul-spec": { "command": "npx", "args": ["-y", "soul-spec-mcp"] },
    "soulos": { "url": "http://localhost:8000/mcp/sse" }
  }
}
```

Browse/install with soul-spec MCP; register + memory with SoulOS MCP after import.

## Curated examples

Pre-converted souls (generate locally): [examples/clawsouls](../examples/clawsouls/README.md).

## Upstream

SoulOS complements ClawSouls — we do not replace the registry or CLI. SoulOS is **not affiliated with or endorsed by ClawSouls** (see [ClawSouls disclaimer](https://github.com/clawsouls/clawsouls#disclaimer)).

Consider adding `"soulos"` to Soul Spec `compatibility.frameworks` for discoverability.

## Legal and attribution

Imported persona **markdown is upstream-licensed** (typically Apache-2.0 or MIT per soul). SoulOS adds HEXACO MSV and merges files into `description` — a **derivative work**. If you redistribute converted souls:

- Honor the SPDX license on each soul (`runtime_config.source.license` after import)
- For Apache-2.0 souls: include license copy and modification notice ([Apache 2.0 §4](https://www.apache.org/licenses/LICENSE-2.0))
- For CC-BY souls: provide attribution (title, author, source, license link)

This repository does **not** commit persona prose. See [examples/clawsouls/ATTRIBUTION.md](../../examples/clawsouls/ATTRIBUTION.md) and [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

Soul Spec: [clawsouls/soulspec](https://github.com/clawsouls/soulspec) (Apache-2.0).

## Related

- [Sidecar integration](sidecar-integration.md)
- [Hybrid API reference](../reference/hybrid-api.md)
- [ClawSouls REST API](https://github.com/clawsouls/soulspec/blob/main/docs/api/rest-api.md)
