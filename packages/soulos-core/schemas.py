"""HTTP request/response models for the SoulOS kernel API."""

from typing import Any

from pydantic import AliasChoices, BaseModel, Field, field_validator

from runtime.turn_contract import TurnContractError, validate_filled_slots_bounds


class MemoryIngest(BaseModel):
    bot_id: str
    content: str
    session_id: str | None = None


class MemoryRetrieve(BaseModel):
    bot_id: str
    query: str
    top_k: int = 5
    session_id: str | None = None


class MemorySync(BaseModel):
    bot_id: str
    workspace_path: str


class MemoryForget(BaseModel):
    bot_id: str
    content_match: str


class MemoryPurgeExpired(BaseModel):
    """Purge session-scoped memories past MEMORY_SESSION_TTL_SECONDS.

    ``bot_id`` optional: omit to purge all bots (operator / CronJob; requires
    auth off or gateway without tenant account). When auth is enabled with an
    account, ``bot_id`` is required.
    """

    bot_id: str | None = None


class ChatRequest(BaseModel):
    bot_id: str
    message: str


class ReflectStateRequest(BaseModel):
    bot_id: str
    message: str
    reflect_async: bool = False


class UpdateStateRequest(BaseModel):
    bot_id: str
    new_msv: dict


class HybridPrepareRequest(BaseModel):
    bot_id: str
    query: str
    top_k: int = 5
    session_id: str | None = None


class HybridCompleteRequest(BaseModel):
    bot_id: str
    summary: str
    user_message: str | None = None
    session_id: str | None = None
    reflect: bool = True
    reflect_async: bool = False
    filled_slots: dict[str, Any] | None = None
    intent: str | None = None
    assistant_text: str | None = None
    expected_version: int | None = None
    idempotency_key: str | None = None
    advance: bool = True
    expected_step: str | None = None

    @field_validator("filled_slots")
    @classmethod
    def _bounds_filled_slots(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value
        try:
            validate_filled_slots_bounds(value)
        except TurnContractError as e:
            raise ValueError(e.detail) from e
        return value


class EnsureAvatarRequest(BaseModel):
    external_key: str
    soul: dict[str, Any]
    runtime_config: dict[str, Any] | None = None


class ImportSoulPackRequest(BaseModel):
    pack_id: str
    external_key: str | None = None
    msv_preset: str | None = None
    persist: bool = Field(
        default=True, validation_alias=AliasChoices("persist", "register")
    )
    runtime_config: dict[str, Any] | None = None
