# Evolution Matrix — alignment with current SoulOS (v0.1)

This maps the [Evolution Matrix TDD](evolution-matrix.md) to what ships today in `soulos-core`, Soul Studio, and `spec/soul.schema.json`.

## Summary

| TDD pillar | Today (main) | Status |
|------------|--------------|--------|
| `.soul` front matter | `.soul` + `.soul.json`; `soul_compile.py` | **Shipped (Phase 1)** |
| Dual-process debugger | `cognitive_state` SSE + Studio rails | **Shipped (Phase 2)** |
| Git memory ledger | `.soul-memory/`, sync API, CLI | **Shipped (Phase 3)** |

---

## 1. `.soul` format

### What exists

- `spec/soul.schema.json` — `name`, `role`, `description`, `attachment_style`, `baseline_msv`
- HEXACO keys: `H`, `E`, `X`, `A`, `C`, `O` (not `honesty_humility` spellings)
- `packages/soulos-core/soul_validation.py` — Pydantic + jsonschema
- Studio Wizard + export → `*.soul.json`
- `POST /v1/avatars` accepts JSON body only

### TDD deltas

| TDD field | Action for Phase 1 |
|-----------|-------------------|
| YAML `psychology.hexaco.*` long names | Map to `H,E,X,A,C,O` in compiler |
| `engine.llm`, `mcp_compatibility` | New optional `engine` block in compiled object; kernel already pluggable via env |
| `dual_process.system1_threshold` | New runtime config; not in schema today |
| Markdown sections (Identity, Rules) | Compile into `description` + optional `soul_sections` metadata or append to `description` with headers |
| `id`, `version` in front matter | Optional marketplace metadata; extend schema or store in sidecar |

### Recommended Phase 1 deliverables

1. `packages/soulos-core/soul_compile.py` — parse `.soul`, emit dict matching `SoulFile`
2. `register_avatar` / `POST /v1/avatars` — accept `.soul` path or `Content-Type` discrimination
3. Studio: Export as `.soul` + keep `.soul.json` export
4. **No break:** all existing `examples/*.soul.json` unchanged

---

## 2. Dual-process visual debugger

### What exists

- `runtime/pipeline.py` — streams System 1 tokens
- `runtime/reflector.py` — System 2 MSV JSON
- SSE: `event: message`, `event: msv_update`
- Studio chat updates sliders/radar on `msv_update`

### TDD deltas

| TDD | Action for Phase 2 |
|-----|-------------------|
| `event: cognitive_state` | Add alongside `msv_update` (do not remove — backward compat) |
| `confidence_score`, `loop_count`, `active_mcp_tools` | Instrument pipeline + reflector; MCP tool hooks in reflector path |
| Studio split-rail UI | New panel in `studio.js` subscribed to `cognitive_state` |
| Threshold from `.soul` | Read `dual_process.system1_threshold` after Phase 1 compiler |

---

## 3. Git-backed episodic memory

### What exists

- `episodic_memories` table — Postgres, vector(768), kernel-only
- `POST /memory/ingest`, `retrieve` via embedder + pgvector
- MCP `ingest_memory` / `retrieve_memory`
- No workspace-local memory files

### TDD deltas

| TDD | Recommendation |
|-----|----------------|
| Replace vector DB entirely | **Risky for RAG quality** — prefer **hybrid**: `.soul-memory/` as source of truth for team sync, kernel **hydrates** pgvector on boot/sync |
| `YYYY-MM-DD_HASH.jsonl` | Implement writer in SDK or CLI `soulos memory append` |
| `.soulignore` | New file + scanner before append (mirror `.gitignore` patterns + secret regex) |
| TDD mentions SQLite | Current stack is **Postgres** — Phase 3 should say "deprecate kernel-only opaque storage" not SQLite |

### Recommended Phase 3 deliverables

1. Schema for `.jsonl` episode lines + `index.json`
2. `packages/soulos-core/runtime/memory_sync.py` — ingest directory → pgvector
3. Git-friendly CLI: `soulos memory export` / `import` from workspace
4. Document: team workflow (commit `.soul-memory/`, CI does not embed secrets)

---

## 4. Suggested implementation order

```text
Phase 1 (2–3 weeks)
  soul_compile.py, tests, Studio export .soul, docs

Phase 2 (2–3 weeks)
  cognitive_state SSE, Studio rails, pipeline metrics

Phase 3 (3–4 weeks)
  .soul-memory writer, sync to pgvector, .soulignore, SDK helpers
```

---

## Docs & tutorials to update when Phase 1 lands

- `spec/soul.schema.json` — optional `$id` / v2 notes
- `docs/reference/soul-standard.md`
- `docs/guides/python-bot.md` — register from `.soul`
- Studio tutorials + Wizard export format
- `llms.txt` / `SOULOS_AGENT_CONTEXT.md`
