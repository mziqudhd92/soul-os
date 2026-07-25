"""Unit tests for Phase A multi-agent handoff helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from soulos.handoff import (
    HandoffPacket,
    conversation_session_id,
    format_handoff_note,
    handoff_to,
    role_external_key,
)
from soulos.hybrid import SoulHybridClient


def test_role_external_key():
    assert role_external_key("acme", "customer") == "org:acme:customer"
    assert role_external_key("acme", "Inventory Desk") == "org:acme:inventory-desk"


def test_role_external_key_rejects_empty_or_colon():
    with pytest.raises(ValueError):
        role_external_key("", "customer")
    with pytest.raises(ValueError):
        role_external_key("ac:me", "customer")


def test_conversation_session_id():
    assert conversation_session_id("thread-9") == "conv:thread-9"
    assert conversation_session_id("conv:thread-9") == "conv:thread-9"


def test_format_handoff_note():
    note = format_handoff_note(
        HandoffPacket(
            from_role="customer",
            to_role="inventory",
            conversation_id="t1",
            reason="check stock",
            summary="User wants SKU-42 qty",
            payload={"sku": "SKU-42"},
        )
    )
    assert "[SoulOS handoff]" in note
    assert "from_role: customer" in note
    assert "to_role: inventory" in note
    assert "payload.sku: SKU-42" in note


@pytest.mark.asyncio
async def test_handoff_to_complete_then_ingest():
    client = SoulHybridClient(base_url="http://kernel.test", enabled=True)

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [
            httpx.Response(200, json={"status": "success", "ingested": True}),
            httpx.Response(200, json={"status": "success"}),
        ]
        result = await handoff_to(
            client,
            from_bot_id="bot-customer",
            to_bot_id="bot-inventory",
            from_role="customer",
            to_role="inventory",
            conversation_id="thread-1",
            reason="stock check",
            summary="Need SKU-42 availability",
            payload={"sku": "SKU-42"},
        )

    assert result["to_bot_id"] == "bot-inventory"
    assert result["session_id"] == "conv:thread-1"
    assert "SKU-42" in result["note"]
    assert mock_req.await_count == 2
    complete_call = mock_req.await_args_list[0]
    assert complete_call.args[0] == "POST"
    assert complete_call.args[1] == "/hybrid/complete"
    assert complete_call.kwargs["json_body"]["bot_id"] == "bot-customer"
    assert complete_call.kwargs["json_body"]["session_id"] == "conv:thread-1"
    ingest_call = mock_req.await_args_list[1]
    assert ingest_call.args[1] == "/memory/ingest"
    assert ingest_call.kwargs["json_body"]["bot_id"] == "bot-inventory"
    assert "[SoulOS handoff]" in ingest_call.kwargs["json_body"]["content"]


@pytest.mark.asyncio
async def test_handoff_to_rejects_same_bot():
    client = SoulHybridClient(base_url="http://kernel.test", enabled=True)
    with pytest.raises(ValueError, match="must differ"):
        await handoff_to(
            client,
            from_bot_id="same",
            to_bot_id="same",
            from_role="a",
            to_role="b",
            conversation_id="t",
            reason="x",
            summary="y",
        )


@pytest.mark.asyncio
async def test_ingest_memory_on_hybrid_client():
    client = SoulHybridClient(base_url="http://kernel.test", bot_id="bot-1", enabled=True)
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = httpx.Response(200, json={"status": "success"})
        out = await client.ingest_memory("fact", session_id="conv:1")
    assert out == {"status": "success"}
    mock_req.assert_awaited_once()
    assert mock_req.await_args.kwargs["json_body"] == {
        "bot_id": "bot-1",
        "content": "fact",
        "session_id": "conv:1",
    }
