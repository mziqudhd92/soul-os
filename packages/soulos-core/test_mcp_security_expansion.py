"""Security + cognitive MCP expansion negative/happy tests (TDD ship gate)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from auth import AccountContext, set_mcp_account_context
from mcp_server import handle_call_tool, handle_list_tools, set_mcp_security_context
from runtime.errors import ACCESS_DENIED
from runtime.security_context import (
    SCOPE_MCP_ADMIN_MSV_WRITE,
    security_context_from_account,
)


@pytest.fixture(autouse=True)
def _reset():
    set_mcp_security_context(None)
    set_mcp_account_context(AccountContext(account_id=None))
    yield
    set_mcp_security_context(None)


@pytest.mark.asyncio
async def test_admin_tool_hidden_without_scope():
    names = {t.name for t in await handle_list_tools()}
    assert "update_cognitive_state" not in names
    assert "apply_msv_delta" in names
    assert "reflect_cognitive_state" in names


@pytest.mark.asyncio
async def test_admin_tool_listed_with_scope():
    set_mcp_security_context(
        security_context_from_account(
            AccountContext(account_id=None),
            scopes=frozenset({SCOPE_MCP_ADMIN_MSV_WRITE}),
        )
    )
    names = {t.name for t in await handle_list_tools()}
    assert "update_cognitive_state" in names


@pytest.mark.asyncio
async def test_force_update_denied_without_admin():
    result = await handle_call_tool(
        "update_cognitive_state",
        {"bot_id": "bot-1", "new_msv": {"hexaco": {k: 0.0 for k in "HEXACO"}}},
    )
    body = json.loads(result[0].text)
    assert body["error"] is True
    assert body["code"] == ACCESS_DENIED


@pytest.mark.asyncio
async def test_apply_msv_delta_requires_appraisal():
    result = await handle_call_tool(
        "apply_msv_delta",
        {"bot_id": "bot-1", "trait": "E", "shift": "slight_increase"},
    )
    body = json.loads(result[0].text)
    assert body["error"] is True
    assert "appraisal_reasoning" in body["detail"]


@pytest.mark.asyncio
async def test_idor_reflect_denied_cross_tenant():
    from runtime.errors import SoulOSProblem

    acct = AccountContext(account_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    set_mcp_account_context(acct)
    set_mcp_security_context(security_context_from_account(acct))
    with (
        patch("mcp_server.engine") as mock_engine,
        patch(
            "runtime.cognitive_msv.verify_bot_access",
            new_callable=AsyncMock,
            side_effect=SoulOSProblem(ACCESS_DENIED, 403, "Access denied"),
        ),
    ):
        mock_engine.connect.return_value.__aenter__.return_value = AsyncMock()
        result = await handle_call_tool(
            "reflect_cognitive_state",
            {
                "appraisal_reasoning": "charged",
                "bot_id": "tenant-b-bot",
                "message": "hi",
            },
        )
    body = json.loads(result[0].text)
    assert body["status"] == 403
    assert body["code"] == ACCESS_DENIED


@pytest.mark.asyncio
async def test_create_handoff_requires_structured_fields():
    result = await handle_call_tool(
        "create_handoff",
        {
            "from_bot_id": "a",
            "to_bot_id": "b",
            "from_role": "r1",
            "to_role": "r2",
            "conversation_id": "conv:1",
            "reason": "x",
            "summary": "y",
        },
    )
    body = json.loads(result[0].text)
    assert body["error"] is True
    assert "task_summary" in body["detail"]


@pytest.mark.asyncio
async def test_streamable_session_hijack_rejected(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", False)
    from main import app
    from routes import mcp as mcp_routes

    mcp_routes._mcp_sessions.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Tenant A opens session
        r1 = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={
                "X-SoulOS-Account-Id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "X-SoulOS-Gateway-Secret": "changeme_gateway_secret",
                "Host": "localhost",
            },
        )
        assert r1.status_code == 200
        sid = r1.headers.get("mcp-session-id")
        assert sid

        # Tenant B reuses session id
        r2 = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers={
                "Mcp-Session-Id": sid,
                "X-SoulOS-Account-Id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                "X-SoulOS-Gateway-Secret": "changeme_gateway_secret",
                "Host": "localhost",
            },
        )
        assert r2.status_code == 403


@pytest.mark.asyncio
async def test_streamable_body_limit(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", False)
    monkeypatch.setattr("config.MCP_MAX_BODY_BYTES", 64)
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/mcp",
            content=b"x" * 128,
            headers={"Host": "localhost", "Content-Type": "application/json"},
        )
        assert r.status_code == 413


@pytest.mark.asyncio
async def test_parity_tools_listed():
    names = {t.name for t in await handle_list_tools()}
    assert {
        "ingest_conversation_memory",
        "retrieve_conversation_memory",
        "create_handoff",
        "consolidate_memory",
        "apply_msv_delta",
        "reflect_cognitive_state",
    } <= names


@pytest.mark.asyncio
async def test_security_context_is_task_local():
    """Concurrent tasks must not share SecurityContext (ContextVar, not global)."""
    import asyncio

    from mcp_server import get_mcp_security_context, set_mcp_security_context

    results: list[str | None] = []

    async def run_with(account: str, delay: float):
        set_mcp_security_context(
            security_context_from_account(AccountContext(account_id=account))
        )
        await asyncio.sleep(delay)
        results.append(get_mcp_security_context().account_id)

    await asyncio.gather(
        run_with("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", 0.02),
        run_with("bbbbbbbb-cccc-dddd-eeee-ffffffffffff", 0.01),
    )
    assert set(results) == {
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    }


@pytest.mark.asyncio
async def test_host_allowlist_empty_allows_gateway_hostname(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", False)
    monkeypatch.setattr("config.MCP_HOST_ALLOWLIST", [])
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Host": "soulos-kernel"},
        )
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_host_allowlist_rejects_when_configured(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", False)
    monkeypatch.setattr("config.MCP_HOST_ALLOWLIST", ["localhost"])
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Host": "evil.example"},
        )
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_streamable_lists_prompts_and_resource_templates(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", False)
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        init = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Host": "localhost"},
        )
        sid = init.headers.get("mcp-session-id")
        prompts = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "prompts/list"},
            headers={"Host": "localhost", "Mcp-Session-Id": sid},
        )
        assert prompts.status_code == 200
        names = {p["name"] for p in prompts.json()["result"]["prompts"]}
        assert "hybrid_turn" in names

        templates = await ac.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 3, "method": "resources/templates/list"},
            headers={"Host": "localhost", "Mcp-Session-Id": sid},
        )
        assert templates.status_code == 200
        uris = {
            t["uriTemplate"]
            for t in templates.json()["result"]["resourceTemplates"]
        }
        assert "msv://drift/{bot_id}" in uris
