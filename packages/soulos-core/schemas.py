"""HTTP request/response models for the SoulOS kernel API."""

from typing import Any

from pydantic import BaseModel


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


class EnsureAvatarRequest(BaseModel):
    external_key: str
    soul: dict[str, Any]
    runtime_config: dict[str, Any] | None = None
