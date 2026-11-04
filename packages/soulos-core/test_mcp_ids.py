"""Unit tests for MCP ID / URI validation."""

import pytest

from runtime.mcp_ids import (
    McpIdError,
    parse_resource_uri,
    validate_bot_id,
    validate_session_id,
)


def test_validate_bot_id_ok():
    assert validate_bot_id("bot-1") == "bot-1"
    assert validate_bot_id("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def test_validate_bot_id_rejects_traversal():
    with pytest.raises(McpIdError):
        validate_bot_id("../etc/passwd")
    with pytest.raises(McpIdError):
        validate_bot_id("bot%2e%2e%2f")


def test_validate_session_id_rejects_path():
    with pytest.raises(McpIdError):
        validate_session_id("a/b")
    with pytest.raises(McpIdError):
        validate_session_id("..")


def test_parse_memory_uri_limit():
    p = parse_resource_uri("memory://episodic/bot-1?limit=10")
    assert p.kind == "episodic"
    assert p.bot_id == "bot-1"
    assert p.limit == 10


def test_parse_rejects_traversal_uri():
    with pytest.raises(McpIdError):
        parse_resource_uri("memory://episodic/../secret")


def test_parse_msv_drift():
    p = parse_resource_uri("msv://drift/bot-1")
    assert p.kind == "drift"


def test_parse_session_turn():
    p = parse_resource_uri("session://turn/bot-1/sess.1")
    assert p.kind == "turn"
    assert p.session_id == "sess.1"
