"""Turn contract result types and limits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_SLOTS_BYTES = 64 * 1024
MAX_SLOT_DEPTH = 3
MAX_SLOT_KEYS = 50


class TurnContractError(Exception):
    """Raised for payload bound violations before apply_turn."""

    def __init__(self, detail: str, *, code: str = "TURN_CONTRACT_VIOLATION") -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


@dataclass
class TurnApplyResult:
    ok: bool
    step: str
    slots: dict[str, Any]
    advanced: bool = False
    missing_slots: list[str] | None = None
    invalid_slots: dict[str, str] | None = None
    remedial_prompt_hint: str | None = None
    code: str | None = None
    detail: str | None = None
