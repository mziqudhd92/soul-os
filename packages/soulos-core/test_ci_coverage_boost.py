"""Targeted unit tests to keep package coverage above the CI fail-under gate."""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from auth import AccountContext
from runtime.cognitive_msv import (
    apply_msv_delta,
    msv_drift_payload,
    reflect_cognitive_state,
)
from runtime.errors import SOUL_INVALID, SoulOSProblem
from runtime.log_redact import SecretRedactFilter, install_secret_redact_filter
from runtime.mcp_ids import (
    McpIdError,
    parse_resource_uri,
    validate_bot_id,
    validate_session_id,
)
from runtime.mcp_outbound import load_allowed_mcp_servers, run_budgeted_outbound_calls
from runtime.security_context import (
    SCOPE_MCP_ADMIN_MSV_WRITE,
    security_context_from_account,
)
from soul_validation import default_msv_dict


def test_secret_redact_filter_and_install():
    filt = SecretRedactFilter()
    rec = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz",
        args=(),
        exc_info=None,
    )
    assert filt.filter(rec) is True
    assert "[REDACTED]" in rec.getMessage()

    broken = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="%d",
        args=("not-an-int",),
        exc_info=None,
    )
    # Broken formatting should not raise / should pass through.
    assert filt.filter(broken) is True

    install_secret_redact_filter()
    install_secret_redact_filter()  # idempotent
    root = logging.getLogger()
    assert any(isinstance(f, SecretRedactFilter) for f in root.filters)


def test_security_context_admin_tools_env_flag():
    ctx = security_context_from_account(
        AccountContext(account_id=None),
        admin_tools_enabled=True,
    )
    assert ctx.has_admin_msv_write()
    assert SCOPE_MCP_ADMIN_MSV_WRITE in ctx.scopes


def test_msv_drift_payload_coerces_non_dicts():
    out = msv_drift_payload({"baseline_msv": "x", "current_msv": None})
    assert out["baseline_msv"] == {}
    assert out["current_msv"] == {}
    assert "delta" in out
    assert "behavioral_summary" in out


def test_mcp_id_edge_cases():
    with pytest.raises(McpIdError):
        validate_bot_id(None)
    with pytest.raises(McpIdError):
        validate_bot_id("")
    with pytest.raises(McpIdError):
        validate_bot_id("bad/id")
    with pytest.raises(McpIdError):
        validate_session_id(None, required=True)
    assert validate_session_id(None, required=False) is None
    with pytest.raises(McpIdError):
        validate_session_id(123)  # type: ignore[arg-type]
    with pytest.raises(McpIdError):
        validate_session_id("ok%2fno")

    with pytest.raises(McpIdError):
        parse_resource_uri("")
    with pytest.raises(McpIdError):
        parse_resource_uri("memory://episodic/*")
    with pytest.raises(McpIdError):
        parse_resource_uri("memory://episodic/a/b")
    with pytest.raises(McpIdError):
        parse_resource_uri("soul://identity/")
    with pytest.raises(McpIdError):
        parse_resource_uri("msv://drift/a/b")
    with pytest.raises(McpIdError):
        parse_resource_uri("session://turn/bot-1")
    with pytest.raises(McpIdError):
        parse_resource_uri("memory://episodic/bot-1?limit=abc")
    with pytest.raises(McpIdError):
        parse_resource_uri("memory://episodic/bot-1?limit=9999")
    with pytest.raises(McpIdError):
        parse_resource_uri("ftp://other/x")

    assert parse_resource_uri("soul://schema").kind == "schema"
    assert parse_resource_uri("soul://identity/bot-1").kind == "identity"


@pytest.mark.asyncio
async def test_load_allowed_mcp_servers_variants():
    class Row:
        def __init__(self, cfg):
            self.runtime_config = cfg

    class Result:
        def __init__(self, row):
            self._row = row

        def fetchone(self):
            return self._row

    class Conn:
        def __init__(self, row):
            self._row = row

        async def execute(self, *_a, **_k):
            return Result(self._row)

    assert await load_allowed_mcp_servers(Conn(None), "b") is None
    assert await load_allowed_mcp_servers(Conn(Row(None)), "b") is None
    assert await load_allowed_mcp_servers(Conn(Row("{not-json")), "b") is None
    assert await load_allowed_mcp_servers(Conn(Row([1, 2])), "b") is None
    assert await load_allowed_mcp_servers(Conn(Row({})), "b") is None
    assert await load_allowed_mcp_servers(Conn(Row({"allowed_mcp_servers": "x"})), "b") == []
    assert await load_allowed_mcp_servers(
        Conn(Row({"allowed_mcp_servers": ["ext"]})), "b"
    ) == ["ext"]
    assert await load_allowed_mcp_servers(
        Conn(Row(json.dumps({"allowed_mcp_servers": ["a"]}))), "b"
    ) == ["a"]


@pytest.mark.asyncio
async def test_run_budgeted_outbound_disabled_and_errors(monkeypatch):
    from runtime import mcp_client

    monkeypatch.setattr(mcp_client, "SOULOS_MCP_CLIENT", False)
    mcp_client.set_outbound_client(mcp_client.OutboundMcpClient(config=mcp_client.OutboundMcpConfig()))
    assert await run_budgeted_outbound_calls([{"name": "x"}]) == []

    monkeypatch.setattr(mcp_client, "SOULOS_MCP_CLIENT", True)
    client = mcp_client.OutboundMcpClient(
        config=mcp_client.OutboundMcpConfig(
            servers=[
                mcp_client.OutboundServerConfig(
                    name="ext",
                    url="https://example.com/mcp",
                    allow_tools=[mcp_client.AllowToolSpec(name="search")],
                )
            ]
        )
    )

    async def boom(*_a, **_k):
        raise RuntimeError("down")

    client.call_tool = boom  # type: ignore[method-assign]
    mcp_client.set_outbound_client(client)
    out = await run_budgeted_outbound_calls([{"name": "ext__search", "arguments": {"q": 1}}])
    assert "failed" in out[0]


@pytest.mark.asyncio
async def test_apply_msv_delta_validation_paths():
    with pytest.raises(SoulOSProblem) as ei:
        await apply_msv_delta(
            AsyncMock(),
            AccountContext(account_id=None),
            bot_id="bot-1",
            appraisal_reasoning="   ",
            trait="H",
            shift="slight_increase",
        )
    assert ei.value.code == SOUL_INVALID

    msv = default_msv_dict()
    row = MagicMock()
    row.current_msv = msv
    row.baseline_msv = json.dumps(msv)

    result = MagicMock()
    result.fetchone.return_value = row
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=result)

    with pytest.raises(SoulOSProblem) as ei2:
        await apply_msv_delta(
            conn,
            AccountContext(account_id=None),
            bot_id="bot-1",
            appraisal_reasoning="because trust rose",
            trait="Z",
            shift="slight_increase",
        )
    assert ei2.value.code == SOUL_INVALID


@pytest.mark.asyncio
async def test_apply_msv_delta_success_and_bot_missing():
    msv = default_msv_dict()
    row = MagicMock()
    row.current_msv = json.dumps(msv)
    row.baseline_msv = msv

    ok = MagicMock()
    ok.fetchone.return_value = row
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=ok)

    out = await apply_msv_delta(
        conn,
        AccountContext(account_id=None),
        bot_id="bot-1",
        appraisal_reasoning="user was calm and honest",
        trait="H",
        shift="slight_increase",
    )
    assert out["status"] == "success"
    assert out["trait"] == "H"

    missing = MagicMock()
    missing.fetchone.return_value = None
    conn2 = AsyncMock()
    conn2.execute = AsyncMock(return_value=missing)
    with pytest.raises(SoulOSProblem) as ei:
        await apply_msv_delta(
            conn2,
            AccountContext(account_id=None),
            bot_id="missing",
            appraisal_reasoning="reason",
            trait="H",
            shift="slight_increase",
        )
    assert ei.value.status == 404


@pytest.mark.asyncio
async def test_reflect_cognitive_state_requires_appraisal():
    with pytest.raises(SoulOSProblem) as ei:
        await reflect_cognitive_state(
            AsyncMock(),
            MagicMock(),
            AccountContext(account_id=None),
            bot_id="bot-1",
            message="hi",
            appraisal_reasoning="",
        )
    assert ei.value.code == SOUL_INVALID
