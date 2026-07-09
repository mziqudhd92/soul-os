"""Tests for SoulHybridClient run_turn and Problem Details errors."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from soulos.hybrid import SoulHybridClient, SoulOSError


@pytest.mark.asyncio
async def test_run_turn_flow():
    client = SoulHybridClient(base_url="http://kernel.test", bot_id="bot-1", enabled=True)

    prepare_body = {
        "bot_id": "bot-1",
        "system_prompt": "You are Support Bot.",
        "memories": [],
        "inner_monologue": "Ready.",
        "identity": {},
    }

    async def fake_generate(prompt: str, ctx: dict) -> str:
        assert "Support Bot" in prompt
        return "Refunds within 30 days."

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [
            httpx.Response(200, json=prepare_body),
            httpx.Response(200, json={"status": "success", "ingested": True}),
        ]
        result = await client.run_turn("refund?", fake_generate)
    assert result["reply"] == "Refunds within 30 days."
    assert result["system_prompt"] == prepare_body["system_prompt"]


def test_parse_problem_error():
    resp = httpx.Response(
        404,
        headers={"content-type": "application/problem+json"},
        content=json.dumps(
            {
                "type": "https://soulos.dev/problems/bot-not-found",
                "title": "Bot not found",
                "status": 404,
                "detail": "Bot not found: x",
                "code": "BOT_NOT_FOUND",
            }
        ).encode(),
    )
    from soulos.hybrid import _parse_problem

    err = _parse_problem(resp)
    assert err.code == "BOT_NOT_FOUND"
    assert err.status == 404
