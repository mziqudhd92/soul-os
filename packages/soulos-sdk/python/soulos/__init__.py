from soulos.client import SoulOSClient
from soulos.handoff import (
    HandoffPacket,
    conversation_session_id,
    format_handoff_note,
    handoff_to,
    role_external_key,
)
from soulos.hybrid import SoulHybridClient, SoulOSError, merge_contract_into_system_prompt

__all__ = [
    "SoulOSClient",
    "SoulHybridClient",
    "SoulOSError",
    "merge_contract_into_system_prompt",
    "HandoffPacket",
    "conversation_session_id",
    "format_handoff_note",
    "handoff_to",
    "role_external_key",
]
