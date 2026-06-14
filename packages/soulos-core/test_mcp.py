import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from auth import AccountContext, set_mcp_account_context
from config import GATEWAY_SECRET
from soul_validation import default_msv_dict


VALID_MSV = default_msv_dict()

VALID_SOUL = {
    "name": "MCP Bot",
    "role": "Assistant",
    "description": "Test soul via MCP.",
    "attachment_style": "Secure",
    "baseline_msv": VALID_MSV,
    "status": "available",
}


@pytest.mark.asyncio
async def test_mcp_sse_rejects_unauthenticated_cloud_mode(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", True)
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/mcp/sse")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mcp_messages_rejects_unauthenticated_cloud_mode(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", True)
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/mcp/messages")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mcp_update_cognitive_state_validates_msv():
    from mcp_server import handle_call_tool

    with pytest.raises(ValueError, match="MSV validation failed"):
        await handle_call_tool(
            "update_cognitive_state",
            {
                "bot_id": "bot-1",
                "new_msv": json.dumps({"hexaco": {"H": 9.0}}),
            },
        )


@pytest.mark.asyncio
async def test_mcp_update_cognitive_state_checks_tenant_access():
    from mcp_server import handle_call_tool

    set_mcp_account_context(
        AccountContext(account_id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
    )

    mock_conn = AsyncMock()
    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock) as mock_verify,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_verify.side_effect = HTTPException(status_code=403, detail="Access denied")

        with pytest.raises(HTTPException) as exc:
            await handle_call_tool(
                "update_cognitive_state",
                {"bot_id": "bot-1", "new_msv": json.dumps(VALID_MSV)},
            )
        assert exc.value.status_code == 403
        mock_verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_ingest_memory_uses_embedder():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()

    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock),
        patch("mcp_server.ingest_memory_record", new_callable=AsyncMock) as mock_ingest,
        patch("mcp_server._embedder") as mock_embedder,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        result = await handle_call_tool(
            "ingest_memory",
            {"bot_id": "bot-1", "content": "A remembered moment."},
        )

        mock_ingest.assert_awaited_once_with(
            mock_conn, mock_embedder, "bot-1", "A remembered moment."
        )
        payload = json.loads(result[0].text)
        assert payload["status"] == "success"


@pytest.mark.asyncio
async def test_mcp_retrieve_memory():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()

    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock),
        patch(
            "mcp_server.retrieve_memories",
            new_callable=AsyncMock,
            return_value=["Refund within 30 days."],
        ) as mock_retrieve,
        patch("mcp_server._embedder"),
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        result = await handle_call_tool(
            "retrieve_memory",
            {"bot_id": "bot-1", "query": "refund policy", "top_k": 3},
        )

        mock_retrieve.assert_awaited_once()
        payload = json.loads(result[0].text)
        assert payload["memories"] == ["Refund within 30 days."]


@pytest.mark.asyncio
async def test_mcp_retrieve_memory_denies_wrong_tenant():
    from mcp_server import handle_call_tool

    set_mcp_account_context(
        AccountContext(account_id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
    )
    mock_conn = AsyncMock()

    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock) as mock_verify,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_verify.side_effect = HTTPException(status_code=403, detail="Access denied")

        with pytest.raises(HTTPException) as exc:
            await handle_call_tool(
                "retrieve_memory",
                {"bot_id": "bot-1", "query": "refund"},
            )
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_mcp_get_identity():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()
    identity = {
        "bot_id": "bot-1",
        "name": "Support",
        "role": "Agent",
        "description": "Helps users",
        "baseline_msv": VALID_MSV,
        "current_msv": VALID_MSV,
    }

    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock),
        patch(
            "mcp_server.get_bot_identity",
            new_callable=AsyncMock,
            return_value=identity,
        ),
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        result = await handle_call_tool("get_identity", {"bot_id": "bot-1"})
        payload = json.loads(result[0].text)
        assert payload["name"] == "Support"


@pytest.mark.asyncio
async def test_mcp_register_avatar():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()
    record = {
        "id": "new-id",
        "name": "MCP Bot",
        "role": "Assistant",
        "attachment_style": "Secure",
        "baseline_msv": VALID_MSV,
        "current_msv": VALID_MSV,
    }

    with (
        patch("mcp_server.engine") as mock_engine,
        patch(
            "mcp_server.register_avatar_record",
            new_callable=AsyncMock,
            return_value=record,
        ) as mock_register,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        result = await handle_call_tool("register_avatar", {"soul": VALID_SOUL})
        mock_register.assert_awaited_once()
        payload = json.loads(result[0].text)
        assert payload["id"] == "new-id"


@pytest.mark.asyncio
async def test_mcp_list_avatars():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"))
    mock_conn = AsyncMock()

    with (
        patch("mcp_server.engine") as mock_engine,
        patch(
            "mcp_server.list_avatars",
            new_callable=AsyncMock,
            return_value=[{"id": "a1", "name": "Bot", "role": "R", "status": "available"}],
        ) as mock_list,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        result = await handle_call_tool("list_avatars", {"limit": 10})
        mock_list.assert_awaited_once()
        payload = json.loads(result[0].text)
        assert len(payload["avatars"]) == 1


@pytest.mark.asyncio
async def test_mcp_read_soul_identity_resource():
    from mcp_server import handle_read_resource

    identity = {
        "bot_id": "bot-1",
        "name": "Support",
        "role": "Agent",
        "description": "Helps",
        "baseline_msv": VALID_MSV,
        "current_msv": VALID_MSV,
    }
    mock_conn = AsyncMock()

    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock),
        patch(
            "mcp_server.get_bot_identity",
            new_callable=AsyncMock,
            return_value=identity,
        ),
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        text = await handle_read_resource("soul://identity/bot-1")
        payload = json.loads(text)
        assert payload["name"] == "Support"


@pytest.mark.asyncio
async def test_mcp_middleware_sets_account_context_for_authenticated_request(
    monkeypatch,
):
    monkeypatch.setattr("config.REQUIRE_AUTH", True)
    from auth import get_mcp_account_context
    from main import McpAuthMiddleware

    captured = {}

    async def call_next(request):
        captured["ctx"] = get_mcp_account_context()
        from starlette.responses import Response

        return Response(status_code=204)

    middleware = McpAuthMiddleware(app=MagicMock())
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/mcp/sse",
        "headers": [
            (b"x-soulos-account-id", b"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            (b"x-soulos-gateway-secret", GATEWAY_SECRET.encode()),
        ],
    }
    request = MagicMock()
    request.url.path = "/mcp/sse"
    request.headers = {
        "X-SoulOS-Account-Id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "X-SoulOS-Gateway-Secret": GATEWAY_SECRET,
    }
    request.scope = scope

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 204
    assert captured["ctx"].account_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
