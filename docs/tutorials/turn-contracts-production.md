# Turn contracts in production (~40 min)

**Audience:** shipping a hybrid agent with multi-step reliability.

Covers backtracking, idempotent retries, 422/409/404 recovery, payload bounds, and flow authority.

## Prerequisites

- [My first turn contract](my-first-turn-contract.md)
- Guide: [turn-contracts.md](../guides/turn-contracts.md)

## Backtrack with `clear_slots_on_entry`

After reaching `confirm`, send `intent: "edit_dates"` to return to `collect_dates`. Downstream slots listed in `clear_slots_on_entry` are purged so terms/payment cannot auto-complete.

```python
await client.complete_turn(
    summary="user wants to change dates",
    session_id=session_id,
    reflect=False,
    filled_slots={},
    intent="edit_dates",
    expected_version=version,
)
# turn.step == collect_dates; user_agreed_to_terms / payment_method cleared
```

## Idempotent retry (avoid false 409)

```python
key = "logical-turn-42"
body = dict(
    summary="dates",
    session_id=session_id,
    reflect=False,
    filled_slots={"check_in": "2026-09-01", "check_out": "2026-09-05"},
    intent="provide_dates",
    expected_version=0,
    idempotency_key=key,
)
r1 = await client.complete_turn(**body)
# Network drops after kernel success — retry same key + same expected_version:
r2 = await client.complete_turn(**body)
assert r1["turn"]["turn_version"] == r2["turn"]["turn_version"]
```

Do **not** reuse an idempotency key for a *new* logical turn after a 409 rebase.

## Host recovery loops

| Code | Action |
|------|--------|
| `TURN_CONTRACT_VIOLATION` (422) | Show `remedial_prompt_hint`; re-ask user; do not treat assistant turn as committed |
| `TURN_STATE_STALE` (409) | Call `prepare` again; retry complete with new `expected_version` and **new** idempotency key |
| `TURN_SESSION_EXPIRED` (404) | Reset local UI state; `prepare` recreates step 0 |

## Payload bounds

`filled_slots` max **64 KiB**, nesting depth **3**, **50** keys after merge. Oversized patches return 422.

## Flow authority

Add [deploy/authority.json](../../deploy/authority.md) so agents do not treat a frontend-only deploy as the API:

```json
{
  "authority": "Cloud Run API",
  "canonical_deploy": "gcloud run deploy my-hybrid-api",
  "forbidden_surfaces": ["vercel-only frontend deploy"],
  "notes": "Turn contracts are enforced by the SoulOS kernel behind this API."
}
```

## CI dialogues

```bash
npm run test:turn-contracts
```

Scripts: `quiet`, `octoner`, `try_everything`, `backtrack`, `retry_idempotency`, `expired_session` under `packages/soulos-core/testdata/turn_contracts/`.

## Checklist

- [ ] Backtrack clears downstream slots
- [ ] Duplicate `idempotency_key` returns cached success
- [ ] 409 vs 404 handled differently
- [ ] `authority.json` checked in for the product repo
