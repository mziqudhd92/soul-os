# Turn contracts (hybrid reliability)

Optional **structured turn contracts** on the hybrid path make SoulOS a reliability layer for multi-step agents — not only soul/memory.

**Tutorials:** [My first turn contract](../tutorials/my-first-turn-contract.md) · [Turn contracts in production](../tutorials/turn-contracts-production.md)  
**API:** [hybrid-api.md](../reference/hybrid-api.md) · **Schema:** [spec/turn-contract.schema.json](../../spec/turn-contract.schema.json)

## When to use

Use contracts when the host must collect typed slots, refuse bad advances, support backtracking, and handle network retries without corrupting session state. Skip them for open-ended chat.

## Attach a contract

Pass `runtime_config.turn_contract` on `POST /v1/avatars/ensure` (or import-soulpack). Always pass a stable `session_id` on prepare/complete.

## Flow

1. `prepare` → persona `system_prompt` + separate `contract_context` (step, missing slots, `prompt_appendix`, `turn_version`).
2. Host LLM generates; app parses structured `filled_slots` / `intent` (app owns parsing).
3. `complete` with `expected_version`, `filled_slots`, optional `intent`, `idempotency_key`.
4. Kernel merges (null clears), validates after merge, applies `transitions` then `next`, bumps version.

SDK helpers: Python `merge_contract_into_system_prompt` / TypeScript `mergeContractIntoSystemPrompt`. Contract-mode `complete_turn` / `completeTurn` auto-sets `idempotency_key`.

## Transitions and backtracking

Per step, `transitions[intent]` runs first (e.g. `edit_dates` → `collect_dates`). Otherwise soft intents stay; completion uses `next`. On entry to a step, `clear_slots_on_entry` purges listed keys so downstream slots cannot auto-complete after edits.

## Concurrency and retries

- Optimistic lock: `expected_version` must match session `turn_version` → else **409** `TURN_STATE_STALE` (DB compare-and-set).
- Idempotency: same `idempotency_key` after success → cached **200/202** (avoids false 409 on dropped responses).
- Missing/TTL-purged session → **404** `TURN_SESSION_EXPIRED` (not 409).
- `turn_sessions` use the same `MEMORY_SESSION_TTL_SECONDS` as session memory: lazy expire on read, bulk purge via `POST /memory/purge-expired` (`turn_sessions_deleted`), and `DELETE /memory/session/{bot}/{session}` removes the turn row.

## Errors

| Code | HTTP | Action |
|------|------|--------|
| `TURN_CONTRACT_VIOLATION` | 422 | `remedial_prompt_hint` + re-prompt |
| `TURN_REJECT_TOKEN` | 422 | Rewrite assistant text |
| `TURN_STEP_MISMATCH` | 422 | Re-prepare; align `expected_step` |
| `TURN_STATE_STALE` | 409 | Re-prepare; new key |
| `TURN_SESSION_EXPIRED` | 404 | Reset; prepare again |

**Surfaces:** Turn contracts are REST + SDK (`run_turn` / `complete_turn`). Soul Studio chat and MCP tools do **not** drive the contract loop — use hybrid HTTP/SDK.

## CI dialogues

`npm run test:turn-contracts` runs quiet / octoner / try_everything / backtrack / retry_idempotency / expired_session fixtures under `packages/soulos-core/testdata/turn_contracts/`.

## Ownership metadata

Declare deploy authority so coding agents do not “fix” the wrong surface: [authority.md](../deployment/authority.md).
