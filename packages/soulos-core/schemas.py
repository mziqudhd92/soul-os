"""HTTP request/response models for the SoulOS kernel API."""

from pydantic import BaseModel


class MemoryIngest(BaseModel):
    bot_id: str
    content: str


class MemoryRetrieve(BaseModel):
    bot_id: str
    query: str
    top_k: int = 5


class ChatRequest(BaseModel):
    bot_id: str
    message: str


class UpdateStateRequest(BaseModel):
    bot_id: str
    new_msv: dict
