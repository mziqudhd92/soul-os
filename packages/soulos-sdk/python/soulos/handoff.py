"""Phase A multi-agent handoff helpers (app-orchestrated; no kernel teams API).

Register one avatar per specialist role with stable ``external_key`` values,
keep an app-level ``conversation_id``, and on transfer: complete the current
bot, ingest a handoff note into the next bot's memory, then prepare on the next
``bot_id``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from soulos.hybrid import SoulHybridClient


def role_external_key(org_id: str, role: str) -> str:
    """Stable ensure key: ``org:{org_id}:{role}`` (e.g. ``org:acme:customer``)."""
    org = (org_id or "").strip()
    role_slug = (role or "").strip().lower().replace(" ", "-")
    if not org or not role_slug:
        raise ValueError("org_id and role are required")
    if ":" in org or ":" in role_slug:
        raise ValueError("org_id and role must not contain ':'")
    return f"org:{org}:{role_slug}"


def conversation_session_id(conversation_id: str) -> str:
    """Session id shared across specialist turns for the same user thread.

    Kernel memory is still per ``bot_id``; the same string correlates turns in
    your app logs and scopes each bot's episodic memory for that conversation.
    """
    cid = (conversation_id or "").strip()
    if not cid:
        raise ValueError("conversation_id is required")
    if cid.startswith("conv:"):
        return cid
    return f"conv:{cid}"


@dataclass
class HandoffPacket:
    """Structured handoff payload for logging and memory ingest."""

    from_role: str
    to_role: str
    conversation_id: str
    reason: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def format_handoff_note(packet: HandoffPacket) -> str:
    """Plain-text note ingested into the destination bot's memory."""
    lines = [
        "[SoulOS handoff]",
        f"from_role: {packet.from_role}",
        f"to_role: {packet.to_role}",
        f"conversation_id: {packet.conversation_id}",
        f"reason: {packet.reason}",
        f"summary: {packet.summary}",
    ]
    if packet.payload:
        for key in sorted(packet.payload):
            lines.append(f"payload.{key}: {packet.payload[key]}")
    return "\n".join(lines)


async def handoff_to(
    client: SoulHybridClient,
    *,
    from_bot_id: str,
    to_bot_id: str,
    from_role: str,
    to_role: str,
    conversation_id: str,
    reason: str,
    summary: str,
    user_message: str | None = None,
    payload: dict[str, Any] | None = None,
    reflect: bool = False,
) -> dict[str, Any]:
    """Complete the source bot and seed the destination bot with a handoff note.

    Caller should then ``prepare_turn`` on ``to_bot_id`` with the same
    ``conversation_session_id(conversation_id)``.
    """
    if from_bot_id == to_bot_id:
        raise ValueError("from_bot_id and to_bot_id must differ")
    session_id = conversation_session_id(conversation_id)
    packet = HandoffPacket(
        from_role=from_role,
        to_role=to_role,
        conversation_id=conversation_id,
        reason=reason,
        summary=summary,
        payload=dict(payload or {}),
    )
    note = format_handoff_note(packet)
    completed = await client.complete_turn(
        summary=summary,
        user_message=user_message or f"Handoff to {to_role}: {reason}",
        bot_id=from_bot_id,
        session_id=session_id,
        reflect=reflect,
        reflect_async=True,
    )
    ingested = await client.ingest_memory(
        bot_id=to_bot_id,
        content=note,
        session_id=session_id,
    )
    return {
        "to_bot_id": to_bot_id,
        "session_id": session_id,
        "packet": packet.to_dict(),
        "note": note,
        "complete": completed,
        "ingest": ingested,
    }
