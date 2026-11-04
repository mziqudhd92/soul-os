"""Coverage for plan features that were advertised but under-wired."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from runtime.errors import ACCESS_DENIED, SoulOSProblem
from runtime.handoffs import assert_handoff_allowed
from runtime.log_redact import SecretRedactFilter
from runtime.mcp_client import MAX_TOOL_ITERATIONS, OutboundMcpClient, OutboundMcpConfig
from runtime.mcp_outbound import run_budgeted_outbound_calls
from runtime.memory_cognitive import rerank_hits_for_persona
from runtime.memory_consolidate import consolidate_memories
from runtime.memory_rank import MemoryHit
from runtime.memory_trust import TRUST_EXTERNAL_MCP, format_memories_for_reflect
from soul_validation import default_msv_dict


def test_format_memories_for_reflect_quarantines_dicts():
    out = format_memories_for_reflect(
        [
            {"content": "secret tip", "trust_level": TRUST_EXTERNAL_MCP, "source_principal": "p1"},
            "plain memory",
        ]
    )
    assert "<untrusted_memory" in out[0]
    assert "secret tip" in out[0]
    assert out[1] == "plain memory"


def test_quarantine_strips_control_chars():
    from runtime.memory_trust import quarantine_untrusted

    out = quarantine_untrusted(
        "hello\x00world\x1f",
        trust_level=TRUST_EXTERNAL_MCP,
        source_principal="ext",
    )
    assert "\x00" not in out
    assert "\x1f" not in out
    assert "helloworld" in out


def test_rerank_recency_and_mood():
    hits = [
        MemoryHit(content="neutral note", id="1", rrf_score=0.55),
        MemoryHit(content="I feel afraid and upset", id="2", rrf_score=0.50),
    ]
    msv = default_msv_dict()
    msv["hexaco"]["E"] = 0.9
    ranked = rerank_hits_for_persona(
        hits, top_k=2, recency_weight=0.0, mood_congruent=True, current_msv=msv
    )
    assert ranked[0].content.startswith("I feel")


def test_handoff_allowlist_denies():
    with pytest.raises(SoulOSProblem) as ei:
        assert_handoff_allowed(
            from_bot_id="a", to_bot_id="b", allowed_targets=["c"]
        )
    assert ei.value.code == ACCESS_DENIED


def test_handoff_allowlist_none_inherits():
    assert_handoff_allowed(from_bot_id="a", to_bot_id="b", allowed_targets=None)


@pytest.mark.asyncio
async def test_consolidate_too_early():
    class Row:
        def __init__(self, i):
            self.id = f"00000000-0000-0000-0000-00000000000{i}"
            self.content = f"fact {i}"
            self.created_at = None
            self.importance = 0.2

    class Result:
        def fetchall(self):
            return [Row(1), Row(2)]

        def fetchone(self):
            return None

    class Conn:
        async def execute(self, query, params=None):
            return Result()

    emb = AsyncMock()
    out = await consolidate_memories(
        Conn(), emb, "bot-1", limit=8, min_candidates=4
    )
    assert out["status"] == "noop"
    assert out["reason"] == "too_early"


@pytest.mark.asyncio
async def test_rate_limit_reflect_tool():
    from auth import AccountContext, set_mcp_account_context
    from mcp_server import handle_call_tool, set_mcp_security_context
    from runtime.mcp_rate_limit import reflect_limiter
    from runtime.security_context import security_context_from_account

    set_mcp_account_context(AccountContext(account_id="tenant-rate"))
    set_mcp_security_context(
        security_context_from_account(AccountContext(account_id="tenant-rate"))
    )
    # Drain bucket
    key = "tenant-rate:reflect"
    for _ in range(20):
        reflect_limiter.allow(key)
    result = await handle_call_tool(
        "reflect_cognitive_state",
        {
            "appraisal_reasoning": "x",
            "bot_id": "bot-1",
            "message": "hi",
        },
    )
    import json

    body = json.loads(result[0].text)
    assert body["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_outbound_budget_caps_iterations(monkeypatch):
    from runtime.mcp_client import (
        AllowToolSpec,
        OutboundServerConfig,
        set_outbound_client,
    )

    calls = []

    async def fake_call(self, name, arguments, **kwargs):
        calls.append(name)
        return f"<untrusted_tool_output server='t'>{name}</untrusted_tool_output>"

    monkeypatch.setattr(
        "runtime.mcp_client.OutboundMcpClient.call_tool", fake_call
    )
    monkeypatch.setattr("runtime.mcp_client.SOULOS_MCP_CLIENT", True)
    monkeypatch.setattr("runtime.mcp_outbound.get_outbound_client", lambda: client)

    client = OutboundMcpClient(
        config=OutboundMcpConfig(
            servers=[
                OutboundServerConfig(
                    name="ext",
                    url="https://example.com/mcp",
                    allow_tools=[AllowToolSpec(name="search")],
                )
            ]
        )
    )
    set_outbound_client(client)
    planned = [{"name": "ext__search", "arguments": {"q": str(i)}} for i in range(10)]
    out = await run_budgeted_outbound_calls(planned)
    assert len(out) == MAX_TOOL_ITERATIONS
    assert len(calls) == MAX_TOOL_ITERATIONS
    set_outbound_client(None)


def test_secret_redact_filter():
    filt = SecretRedactFilter()
    record = logging.LogRecord(
        name="mcp_client",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz012345",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert "[REDACTED]" in record.getMessage()
    assert "sk-abc" not in record.getMessage()


@pytest.mark.asyncio
async def test_allowed_mcp_servers_empty_disables(monkeypatch):
    monkeypatch.setattr("runtime.mcp_client.SOULOS_MCP_CLIENT", True)
    from runtime.mcp_client import (
        AllowToolSpec,
        OutboundServerConfig,
        set_outbound_client,
    )
    from runtime.mcp_outbound import resolve_active_mcp_tools

    set_outbound_client(
        OutboundMcpClient(
            config=OutboundMcpConfig(
                servers=[
                    OutboundServerConfig(
                        name="ext",
                        url="https://example.com/mcp",
                        allow_tools=[AllowToolSpec(name="search")],
                    )
                ]
            )
        )
    )

    class Conn:
        async def execute(self, query, params=None):
            row = MagicMock()
            row.runtime_config = {"allowed_mcp_servers": []}
            result = MagicMock()
            result.fetchone.return_value = row
            return result

    tools = await resolve_active_mcp_tools(Conn(), "bot-1")
    assert tools == []
    set_outbound_client(None)
