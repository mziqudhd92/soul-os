import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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

    result = await handle_call_tool(
        "update_cognitive_state",
        {
            "bot_id": "bot-1",
            "new_msv": json.dumps({"hexaco": {"H": 9.0}}),
        },
    )
    body = json.loads(result[0].text)
    assert body["error"] is True
    assert body["code"] == "SOUL_INVALID"
    assert "MSV validation failed" in body["detail"]


@pytest.mark.asyncio
async def test_mcp_update_cognitive_state_checks_tenant_access():
    from mcp_server import handle_call_tool
    from runtime.errors import ACCESS_DENIED, SoulOSProblem

    set_mcp_account_context(
        AccountContext(account_id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
    )

    mock_conn = AsyncMock()
    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock) as mock_verify,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_verify.side_effect = SoulOSProblem(ACCESS_DENIED, 403, "Access denied")

        result = await handle_call_tool(
            "update_cognitive_state",
            {"bot_id": "bot-1", "new_msv": json.dumps(VALID_MSV)},
        )
        body = json.loads(result[0].text)
        assert body["error"] is True
        assert body["code"] == ACCESS_DENIED
        assert body["status"] == 403
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
            mock_conn, mock_embedder, "bot-1", "A remembered moment.", None
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
    from runtime.errors import ACCESS_DENIED, SoulOSProblem

    set_mcp_account_context(
        AccountContext(account_id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
    )
    mock_conn = AsyncMock()

    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock) as mock_verify,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_verify.side_effect = SoulOSProblem(ACCESS_DENIED, 403, "Access denied")

        result = await handle_call_tool(
            "retrieve_memory",
            {"bot_id": "bot-1", "query": "refund"},
        )
        body = json.loads(result[0].text)
        assert body["error"] is True
        assert body["code"] == ACCESS_DENIED
        assert body["status"] == 403


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


@pytest.mark.asyncio
async def test_mcp_lists_rest_parity_tools():
    from mcp_server import handle_list_tools

    names = {t.name for t in await handle_list_tools()}
    assert {
        "forget_memory",
        "delete_session",
        "ensure_avatar",
        "hybrid_prepare",
        "hybrid_complete",
    } <= names


@pytest.mark.asyncio
async def test_mcp_retrieve_memory_passes_session_id():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()
    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock),
        patch(
            "mcp_server.retrieve_memories", new_callable=AsyncMock, return_value=[]
        ) as mock_retrieve,
        patch("mcp_server._embedder") as mock_embedder,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        await handle_call_tool(
            "retrieve_memory", {"bot_id": "b", "query": "q", "session_id": "s1"}
        )
    mock_retrieve.assert_awaited_once_with(mock_conn, mock_embedder, "b", "q", 5, "s1")


@pytest.mark.asyncio
async def test_mcp_forget_memory():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()
    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock) as mock_verify,
        patch("mcp_server.forget_memory", new_callable=AsyncMock, return_value=3) as mock_forget,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        result = await handle_call_tool(
            "forget_memory", {"bot_id": "b", "content_match": "old address"}
        )
    mock_verify.assert_awaited_once()
    mock_forget.assert_awaited_once_with(mock_conn, "b", "old address")
    assert json.loads(result[0].text)["deleted"] == 3


@pytest.mark.asyncio
async def test_mcp_forget_memory_requires_match():
    from mcp_server import handle_call_tool

    result = await handle_call_tool("forget_memory", {"bot_id": "b"})
    body = json.loads(result[0].text)
    assert body["error"] is True
    assert body["code"] == "SOUL_INVALID"
    assert "content_match" in body["detail"]


@pytest.mark.asyncio
async def test_mcp_delete_session_clears_memories_and_turn_state():
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()
    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.verify_bot_access", new_callable=AsyncMock),
        patch(
            "mcp_server.delete_session_memories", new_callable=AsyncMock, return_value=2
        ),
        patch(
            "mcp_server.delete_turn_session", new_callable=AsyncMock, return_value=1
        ) as mock_turn,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        result = await handle_call_tool(
            "delete_session", {"bot_id": "b", "session_id": "s1"}
        )
    mock_turn.assert_awaited_once_with(mock_conn, "b", "s1")
    body = json.loads(result[0].text)
    assert body["deleted"] == 2
    assert body["turn_sessions_deleted"] == 1


@pytest.mark.asyncio
async def test_mcp_ensure_avatar_accepts_json_string_soul():
    from mcp_server import handle_call_tool

    account_id = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
    set_mcp_account_context(AccountContext(account_id=account_id))
    mock_conn = AsyncMock()
    with (
        patch("mcp_server.engine") as mock_engine,
        patch(
            "mcp_server.ensure_avatar_record",
            new_callable=AsyncMock,
            return_value={"id": "bot-9", "name": "MCP Bot"},
        ) as mock_ensure,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        result = await handle_call_tool(
            "ensure_avatar",
            {"external_key": "app:user-1", "soul": json.dumps(VALID_SOUL)},
        )
    mock_ensure.assert_awaited_once_with(
        mock_conn, account_id, "app:user-1", VALID_SOUL, None
    )
    assert json.loads(result[0].text)["id"] == "bot-9"
    set_mcp_account_context(AccountContext(account_id=None))


@pytest.mark.asyncio
async def test_mcp_hybrid_prepare_delegates_to_rest_route():
    from mcp_server import handle_call_tool
    from schemas import HybridPrepareRequest

    set_mcp_account_context(AccountContext(account_id=None))
    mock_conn = AsyncMock()
    with (
        patch("mcp_server.engine") as mock_engine,
        patch(
            "mcp_server.hybrid_prepare",
            new_callable=AsyncMock,
            return_value={"bot_id": "b", "system_prompt": "You are..."},
        ) as mock_route,
    ):
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        result = await handle_call_tool(
            "hybrid_prepare", {"bot_id": "b", "query": "hi", "session_id": "s1"}
        )
    kwargs = mock_route.await_args.kwargs
    assert kwargs["db"] is mock_conn
    assert kwargs["payload"] == HybridPrepareRequest(
        bot_id="b", query="hi", session_id="s1"
    )
    assert json.loads(result[0].text)["system_prompt"] == "You are..."
    mock_conn.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_hybrid_complete_async_reflect_runs_background_task():
    import asyncio

    from fastapi.responses import JSONResponse

    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    ran = asyncio.Event()

    async def fake_reflect():
        ran.set()

    async def fake_route(*, payload, background_tasks, **_):
        assert payload.reflect_async is True
        background_tasks.add_task(fake_reflect)
        return JSONResponse(status_code=202, content={"status": "accepted"})

    with (
        patch("mcp_server.engine") as mock_engine,
        patch("mcp_server.hybrid_complete", side_effect=fake_route),
    ):
        mock_engine.connect.return_value.__aenter__.return_value = AsyncMock()
        result = await handle_call_tool(
            "hybrid_complete",
            {
                "bot_id": "b",
                "summary": "User asked about refunds.",
                "user_message": "refund?",
                "reflect_async": True,
            },
        )
        await asyncio.wait_for(ran.wait(), timeout=1)
    assert json.loads(result[0].text)["status"] == "accepted"


@pytest.mark.asyncio
async def test_mcp_hybrid_complete_maps_problem_to_error_code():
    from mcp_server import handle_call_tool
    from runtime.errors import SoulOSProblem

    set_mcp_account_context(AccountContext(account_id=None))
    with (
        patch("mcp_server.engine") as mock_engine,
        patch(
            "mcp_server.hybrid_complete",
            new_callable=AsyncMock,
            side_effect=SoulOSProblem("TURN_STATE_STALE", 409, "version mismatch"),
        ),
    ):
        mock_engine.connect.return_value.__aenter__.return_value = AsyncMock()
        result = await handle_call_tool(
            "hybrid_complete", {"bot_id": "b", "summary": "s", "session_id": "x"}
        )
    payload = json.loads(result[0].text)
    assert payload["error"] is True
    assert payload["code"] == "TURN_STATE_STALE"
    assert payload["status"] == 409
    assert payload["detail"] == "version mismatch"


@pytest.mark.asyncio
async def test_mcp_ingest_memory_rejects_oversized_content():
    from config import MAX_MEMORY_CONTENT_CHARS
    from mcp_server import handle_call_tool

    set_mcp_account_context(AccountContext(account_id=None))
    result = await handle_call_tool(
        "ingest_memory",
        {"bot_id": "bot-1", "content": "x" * (MAX_MEMORY_CONTENT_CHARS + 1)},
    )
    body = json.loads(result[0].text)
    assert body["error"] is True
    assert body["code"] == "SOUL_INVALID"
    assert body["status"] == 422
