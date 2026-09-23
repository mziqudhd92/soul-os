"""Tests for SoulHybridClient run_turn and Problem Details errors."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from soulos.hybrid import (
    SoulHybridClient,
    SoulOSError,
    _parse_problem,
    merge_contract_into_system_prompt,
)


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
    complete_body = mock_req.await_args_list[1].kwargs["json_body"]
    assert "expected_version" not in complete_body


@pytest.mark.asyncio
async def test_run_turn_passes_contract_version():
    client = SoulHybridClient(base_url="http://kernel.test", bot_id="bot-1", enabled=True)
    prepare_body = {
        "bot_id": "bot-1",
        "system_prompt": "You are Concierge.",
        "memories": [],
        "inner_monologue": "Ready.",
        "identity": {},
        "contract_context": {
            "expected_step": "collect_dates",
            "missing_slots": ["check_in"],
            "filled_slots": {},
            "reject_tokens": [],
            "ui_progress": {"step_index": 0, "step_count": 2, "label": "collect_dates"},
            "allowed_intents": [],
            "prompt_appendix": "[SYSTEM DIRECTIVE: Step 'collect_dates'.]",
            "turn_version": 3,
        },
    }

    async def fake_generate(prompt: str, ctx: dict) -> str:
        assert "SYSTEM DIRECTIVE" in prompt
        return "What dates?"

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [
            httpx.Response(200, json=prepare_body),
            httpx.Response(
                200,
                json={"status": "success", "ingested": True, "turn": {"turn_version": 4}},
            ),
        ]
        result = await client.run_turn(
            "book",
            fake_generate,
            session_id="s1",
            filled_slots={"check_in": "2026-09-01"},
            intent="provide_dates",
        )
    assert result["complete"]["turn"]["turn_version"] == 4
    body = mock_req.await_args_list[1].kwargs["json_body"]
    assert body["expected_version"] == 3
    assert body["expected_step"] == "collect_dates"
    assert body["filled_slots"]["check_in"] == "2026-09-01"
    assert body["intent"] == "provide_dates"
    assert body["assistant_text"] == "What dates?"
    assert body["idempotency_key"]


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


def test_parse_problem_non_json():
    resp = httpx.Response(500, text="plain error")
    err = _parse_problem(resp)
    assert err.status == 500
    assert "plain error" in err.detail


def test_merge_contract_appendix_only():
    assert merge_contract_into_system_prompt(
        {"system_prompt": "", "contract_context": {"prompt_appendix": "ONLY"}}
    ) == "ONLY"


@pytest.mark.asyncio
async def test_enabled_from_env(monkeypatch):
    monkeypatch.setenv("SOULOS_ENABLED", "0")
    client = SoulHybridClient(base_url="http://k", bot_id="b")
    assert client.enabled is False


@pytest.mark.asyncio
async def test_close_and_get_client():
    client = SoulHybridClient(base_url="http://k", bot_id="b", enabled=True)
    with patch("soulos.hybrid.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        MockClient.return_value = instance
        c1 = await client._get_client()
        c2 = await client._get_client()
        assert c1 is c2
        await client.close()
        assert client._client is None


@pytest.mark.asyncio
async def test_request_retries_http_error_then_raises():
    client = SoulHybridClient(base_url="http://k", bot_id="b", max_retries=1)
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(side_effect=httpx.ConnectError("down"))
    client._client = mock_http
    with pytest.raises(httpx.ConnectError):
        await client._request("GET", "/ready")


@pytest.mark.asyncio
async def test_is_ready_paths():
    client = SoulHybridClient(base_url="http://k", bot_id="b", enabled=False)
    assert await client.is_ready() is False

    client.enabled = True
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = httpx.Response(200, json={"status": "ok"})
        assert await client.is_ready() is True
        mock_req.return_value = httpx.Response(503, json={"status": "down"})
        # 503 raises SoulOSError via _request logic — simulate by raising
        mock_req.side_effect = SoulOSError("DOWN", 503, "no", {})
        assert await client.is_ready() is False


@pytest.mark.asyncio
async def test_ensure_avatar_dict_soul():
    client = SoulHybridClient(base_url="http://k", enabled=True)
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = httpx.Response(200, json={"id": "bot-9"})
        out = await client.ensure_avatar("app:u", {"name": "X"})
    assert out["id"] == "bot-9"
    assert client.bot_id == "bot-9"


@pytest.mark.asyncio
async def test_complete_turn_soft_fail_http_error():
    client = SoulHybridClient(base_url="http://k", bot_id="b", enabled=True)
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = httpx.ConnectError("down")
        assert await client.complete_turn("s") is None


@pytest.mark.asyncio
async def test_ingest_memory_paths():
    client = SoulHybridClient(base_url="http://k", enabled=False)
    assert await client.ingest_memory("x") is None
    client.enabled = True
    assert await client.ingest_memory("x") is None  # no bot_id
    client.bot_id = "b"
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = httpx.Response(200, json={"status": "ok"})
        out = await client.ingest_memory("fact", session_id="s1")
        assert out["status"] == "ok"
        mock_req.side_effect = SoulOSError("X", 500, "no", {})
        assert await client.ingest_memory("fact") is None


@pytest.mark.asyncio
async def test_run_turn_ensure_and_prepare_fail():
    client = SoulHybridClient(base_url="http://k", enabled=True)
    with patch.object(client, "ensure_avatar", new_callable=AsyncMock) as ensure:
        with patch.object(client, "prepare_turn", new_callable=AsyncMock, return_value=None):
            with pytest.raises(SoulOSError, match="PREPARE_FAILED"):
                await client.run_turn(
                    "q",
                    AsyncMock(),
                    external_key="k",
                    soul={"name": "n"},
                )
            ensure.assert_awaited_once()
