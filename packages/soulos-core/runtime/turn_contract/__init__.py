"""Turn contract resolver — public API (package split from monolith)."""

from runtime.turn_contract.apply import apply_turn
from runtime.turn_contract.bounds import validate_filled_slots_bounds
from runtime.turn_contract.prompts import (
    build_contract_context,
    build_prompt_appendix,
    build_remedial_prompt_hint,
    build_ui_progress,
)
from runtime.turn_contract.schema import validate_turn_contract
from runtime.turn_contract.slots import merge_slots, missing_slots_for_step
from runtime.turn_contract.types import (
    MAX_SLOT_DEPTH,
    MAX_SLOT_KEYS,
    MAX_SLOTS_BYTES,
    TurnApplyResult,
    TurnContractError,
)

__all__ = [
    "MAX_SLOT_DEPTH",
    "MAX_SLOT_KEYS",
    "MAX_SLOTS_BYTES",
    "TurnApplyResult",
    "TurnContractError",
    "apply_turn",
    "build_contract_context",
    "build_prompt_appendix",
    "build_remedial_prompt_hint",
    "build_ui_progress",
    "merge_slots",
    "missing_slots_for_step",
    "validate_filled_slots_bounds",
    "validate_turn_contract",
]
