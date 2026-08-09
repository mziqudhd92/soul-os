# My first turn contract (~20 min)

**Audience:** you already completed [My first sidecar](my-first-sidecar.md) (`ensure → prepare → LLM → complete`).

You will attach a minimal two-step booking-style contract, read `contract_context`, send `filled_slots`, and recover from one **422**.

## Prerequisites

- Kernel running (`docker compose up --build` or local kernel on `:8000`)
- Python with `soulos` SDK, or curl

## 1. Ensure an avatar with a contract

```python
from soulos import SoulHybridClient

CONTRACT = {
    "id": "booking.v1",
    "initial_step": "collect_dates",
    "reject_tokens": ["IGNORE PREVIOUS"],
    "steps": [
        {
            "id": "collect_dates",
            "required_slots": ["check_in", "check_out"],
            "slot_schemas": {
                "check_in": {"type": "string", "format": "date"},
                "check_out": {"type": "string", "format": "date"},
            },
            "allowed_intents": ["provide_dates"],
            "next": "confirm",
            "completion": {"all_required_slots": True},
        },
        {
            "id": "confirm",
            "required_slots": ["user_agreed_to_terms"],
            "slot_schemas": {"user_agreed_to_terms": {"type": "boolean"}},
            "allowed_intents": ["confirm_booking"],
            "transitions": {"confirm_booking": "completed"},
            "next": "completed",
            "completion": {"all_required_slots": True},
        },
        {"id": "completed"},
    ],
}

soul = {
    "name": "Concierge",
    "role": "Booking assistant",
    "description": "Helps collect travel dates.",
    "attachment_style": "Secure",
    "baseline_msv": {
        "hexaco": {"H": 0.8, "E": 0.5, "X": 0.6, "A": 0.8, "C": 0.7, "O": 0.5},
        "moral_foundations": {
            "care_harm": 0.8,
            "fairness_cheating": 0.7,
            "loyalty_betrayal": 0.5,
            "authority_subversion": 0.4,
            "sanctity_degradation": 0.4,
        },
        "drives": {"curiosity": 0.5, "autonomy": 0.4, "social_approval": 0.6},
        "epistemic_uncertainty": 0.2,
        "inner_monologue": "Collect clear dates.",
    },
}

client = SoulHybridClient(base_url="http://localhost:8000")
await client.ensure_avatar(
    "tutorial:turn-contract",
    soul,
    runtime_config={"turn_contract": CONTRACT},
)
```

## 2. Prepare and merge the appendix

```python
from soulos import merge_contract_into_system_prompt

session_id = "tutorial-sess-1"
prepared = await client.prepare_turn("I want to book a trip", session_id=session_id)
assert prepared and "contract_context" in prepared
ctx = prepared["contract_context"]
print(ctx["expected_step"], ctx["missing_slots"], ctx["ui_progress"])
system = merge_contract_into_system_prompt(prepared)
# Call your LLM with `system` + user message…
```

## 3. Complete with filled slots

```python
version = ctx["turn_version"]
done = await client.complete_turn(
    summary="User provided dates",
    user_message="Check in 2026-09-01, out 2026-09-05",
    session_id=session_id,
    reflect=False,
    filled_slots={"check_in": "2026-09-01", "check_out": "2026-09-05"},
    intent="provide_dates",
    expected_version=version,
)
print(done["turn"])  # step should be confirm
```

## 4. Handle one 422

```python
from soulos import SoulOSError

try:
    await client.complete_turn(
        summary="bad date",
        session_id=session_id,
        reflect=False,
        filled_slots={"check_in": "Tuesday", "check_out": "2026-09-05"},
        intent="provide_dates",
        expected_version=done["turn"]["turn_version"],
    )
except SoulOSError as e:
    assert e.code == "TURN_CONTRACT_VIOLATION"
    print(e.body.get("remedial_prompt_hint"))
    print(e.body.get("invalid_slots"))
```

## Checklist

- [ ] `prepare` returns `contract_context` with `turn_version`
- [ ] `system_prompt` stays persona-only until you merge the appendix
- [ ] Valid dates advance to `confirm`
- [ ] Invalid date returns 422 with `remedial_prompt_hint`

**Next:** [Turn contracts in production](turn-contracts-production.md) (backtrack, idempotency, 404/409).
