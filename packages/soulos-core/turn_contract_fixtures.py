"""Shared fixtures for hybrid turn-contract HTTP tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

BOOKING_CONTRACT = {
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
            "clear_slots_on_entry": ["user_agreed_to_terms", "payment_method"],
            "allowed_intents": ["provide_dates", "clarify", "cancel"],
            "transitions": {"cancel": "cancelled"},
            "next": "confirm",
            "completion": {"all_required_slots": True},
        },
        {
            "id": "confirm",
            "required_slots": ["user_agreed_to_terms"],
            "slot_schemas": {
                "check_in": {"type": "string", "format": "date"},
                "check_out": {"type": "string", "format": "date"},
                "user_agreed_to_terms": {"type": "boolean"},
                "payment_method": {"type": "string"},
            },
            "allowed_intents": ["confirm_booking", "edit_dates", "cancel"],
            "transitions": {
                "confirm_booking": "completed",
                "edit_dates": "collect_dates",
                "cancel": "cancelled",
            },
            "next": "completed",
            "completion": {"all_required_slots": True},
        },
        {"id": "completed"},
        {"id": "cancelled"},
    ],
}

BOT_ID = "123e4567-e89b-12d3-a456-426614174000"

_STORE: dict[tuple[str, str], dict[str, Any]] = {}


def clear_turn_store() -> None:
    _STORE.clear()


async def mem_get(db, bot_id: str, session_id: str):
    row = _STORE.get((bot_id, session_id))
    return deepcopy(row) if row else None


async def mem_advance(
    db,
    *,
    bot_id: str,
    session_id: str,
    expected_version: int,
    current_step: str,
    slots: dict,
    turn_version: int,
    last_idempotency_key: str | None = None,
    last_success_response: dict | None = None,
):
    row = _STORE.get((bot_id, session_id))
    if not row or row["turn_version"] != expected_version:
        return False
    row["current_step"] = current_step
    row["slots"] = deepcopy(slots)
    row["turn_version"] = turn_version
    if last_idempotency_key is not None:
        row["last_idempotency_key"] = last_idempotency_key
    if last_success_response is not None:
        row["last_success_response"] = deepcopy(last_success_response)
    return True


async def mem_store_success(
    db,
    *,
    bot_id: str,
    session_id: str,
    turn_version: int,
    last_idempotency_key: str | None,
    last_success_response: dict,
):
    row = _STORE.get((bot_id, session_id))
    if not row or row["turn_version"] != turn_version:
        return
    if last_idempotency_key is not None:
        row["last_idempotency_key"] = last_idempotency_key
    row["last_success_response"] = deepcopy(last_success_response)


async def mem_ensure(db, *, bot_id: str, session_id: str, initial_step: str):
    existing = await mem_get(db, bot_id, session_id)
    if existing:
        return existing
    _STORE[(bot_id, session_id)] = {
        "current_step": initial_step,
        "slots": {},
        "turn_version": 0,
        "last_idempotency_key": None,
        "last_success_response": None,
    }
    return await mem_get(db, bot_id, session_id)
