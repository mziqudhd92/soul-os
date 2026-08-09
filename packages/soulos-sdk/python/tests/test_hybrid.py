"""Tests for SoulHybridClient run_turn and Problem Details errors."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from soulos.hybrid import SoulHybridClient, SoulOSError, _parse_problem


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
    err = _parse_problem(resp)
    assert err.code == "BOT_NOT_FOUND"
    assert err.status == 404


@pytest.mark.asyncio
async def test_prepare_turn_disabled_returns_none():
    client = SoulHybridClient(base_url="http://kernel.test", bot_id="bot-1", enabled=False)
    assert await client.prepare_turn("hello") is None


@pytest.mark.asyncio
async def test_prepare_turn_no_bot_id_returns_none():
    client = SoulHybridClient(base_url="http://kernel.test", enabled=True)
    assert await client.prepare_turn("hello") is None


@pytest.mark.asyncio
async def test_request_retries_on_500():
    client = SoulHybridClient(base_url="http://kernel.test", enabled=True, max_retries=2)
    ok = httpx.Response(200, json={"status": "ok"})

    with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(
            side_effect=[
                httpx.Response(503, json={"detail": "busy"}),
                httpx.Response(503, json={"detail": "busy"}),
                ok,
            ]
        )
        mock_get.return_value = mock_http
        resp = await client._request("GET", "/ready")
    assert resp.status_code == 200
    assert mock_http.request.call_count == 3


@pytest.mark.asyncio
async def test_request_raises_problem_details():
    client = SoulHybridClient(base_url="http://kernel.test", enabled=True)
    problem = httpx.Response(
        404,
        headers={"content-type": "application/problem+json"},
        content=json.dumps(
            {"code": "BOT_NOT_FOUND", "detail": "missing", "status": 404}
        ).encode(),
    )

    with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=problem)
        mock_get.return_value = mock_http
        with pytest.raises(SoulOSError) as exc:
            await client._request("POST", "/hybrid/prepare", json_body={"bot_id": "x"})
    assert exc.value.code == "BOT_NOT_FOUND"


@pytest.mark.asyncio
async def test_ensure_avatar_sets_bot_id(tmp_path):
    soul_path = tmp_path / "bot.soul.json"
    soul_path.write_text(
        json.dumps({"name": "Bot", "role": "R", "description": "d", "attachment_style": "Secure"}),
        encoding="utf-8",
    )
    client = SoulHybridClient(base_url="http://kernel.test", enabled=True)
    record = {"id": "new-bot-id", "name": "Bot"}

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = httpx.Response(200, json=record)
        out = await client.ensure_avatar("ext-key", soul_path)
    assert out["id"] == "new-bot-id"
    assert client.bot_id == "new-bot-id"


@pytest.mark.asyncio
async def test_gateway_headers_passed():
    client = SoulHybridClient(
        base_url="http://kernel.test",
        gateway_secret="secret-1",
        account_id="acct-1",
        enabled=True,
    )
    headers = client._request_headers()
    assert headers["X-SoulOS-Gateway-Secret"] == "secret-1"
    assert headers["X-SoulOS-Account-Id"] == "acct-1"


def test_merge_contract_into_system_prompt():
    from soulos.hybrid import merge_contract_into_system_prompt

    merged = merge_contract_into_system_prompt(
        {
            "system_prompt": "You are a concierge.",
            "contract_context": {
                "prompt_appendix": "[SYSTEM DIRECTIVE: Step collect_dates.]"
            },
        }
    )
    assert merged.startswith("You are a concierge.")
    assert "[SYSTEM DIRECTIVE" in merged


@pytest.mark.asyncio
async def test_complete_turn_auto_idempotency_key_and_slots():
    client = SoulHybridClient(base_url="http://kernel.test", bot_id="bot-1", enabled=True)
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = httpx.Response(
            200, json={"status": "success", "ingested": True, "turn": {"step": "confirm"}}
        )
        out = await client.complete_turn(
            "summary",
            session_id="s1",
            reflect=False,
            filled_slots={"check_in": "2026-09-01"},
            expected_version=0,
            intent="provide_dates",
        )
    assert out and out["turn"]["step"] == "confirm"
    body = mock_req.await_args.kwargs["json_body"]
    assert body["filled_slots"]["check_in"] == "2026-09-01"
    assert body["expected_version"] == 0
    assert body["idempotency_key"]


@pytest.mark.asyncio
async def test_complete_turn_raises_turn_contract_violation():
    client = SoulHybridClient(base_url="http://kernel.test", bot_id="bot-1", enabled=True)
    problem = httpx.Response(
        422,
        headers={"content-type": "application/problem+json"},
        content=json.dumps(
            {
                "code": "TURN_CONTRACT_VIOLATION",
                "detail": "bad",
                "status": 422,
                "remedial_prompt_hint": "Ask again",
                "invalid_slots": {"check_in": "Must match format YYYY-MM-DD"},
            }
        ).encode(),
    )
    with patch.object(client, "_get_client", new_callable=AsyncMock) as mock_get:
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=problem)
        mock_get.return_value = mock_http
        with pytest.raises(SoulOSError) as exc:
            await client.complete_turn(
                "summary",
                session_id="s1",
                reflect=False,
                filled_slots={"check_in": "nope"},
                expected_version=0,
            )
    assert exc.value.code == "TURN_CONTRACT_VIOLATION"
    assert exc.value.body.get("remedial_prompt_hint") == "Ask again"
