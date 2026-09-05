"""Filled-slots payload bounds."""

from __future__ import annotations

import json
from typing import Any

from runtime.turn_contract.types import (
    MAX_SLOT_DEPTH,
    MAX_SLOT_KEYS,
    MAX_SLOTS_BYTES,
    TurnContractError,
)


def _json_size(obj: Any) -> int:
    return len(json.dumps(obj, default=str).encode("utf-8"))


def _max_depth(obj: Any, depth: int = 0) -> int:
    if not isinstance(obj, dict):
        if isinstance(obj, list):
            return max((_max_depth(x, depth + 1) for x in obj), default=depth)
        return depth
    if not obj:
        return depth
    return max(_max_depth(v, depth + 1) for v in obj.values())


def validate_filled_slots_bounds(filled_slots: dict[str, Any] | None) -> None:
    patch = filled_slots or {}
    if not isinstance(patch, dict):
        raise TurnContractError("filled_slots must be an object")
    if _json_size(patch) > MAX_SLOTS_BYTES:
        raise TurnContractError(
            f"filled_slots exceeds {MAX_SLOTS_BYTES} bytes",
            code="TURN_CONTRACT_VIOLATION",
        )
    if _max_depth(patch) > MAX_SLOT_DEPTH:
        raise TurnContractError(
            f"filled_slots nesting depth exceeds {MAX_SLOT_DEPTH}",
            code="TURN_CONTRACT_VIOLATION",
        )
    if len(patch) > MAX_SLOT_KEYS:
        raise TurnContractError(
            f"filled_slots has more than {MAX_SLOT_KEYS} keys",
            code="TURN_CONTRACT_VIOLATION",
        )
