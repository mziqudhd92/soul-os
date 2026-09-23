"""Unit tests for runtime.avatars helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from runtime import avatars
from runtime.turn_contract import TurnContractError

VALID_SOUL = {
    "name": "Runtime Avatar",
    "role": "Tester",
    "description": "Avatar unit test payload.",
    "attachment_style": "Secure",
    "baseline_msv": {
        "hexaco": {"H": 0.5, "E": 0.5, "X": 0.5, "A": 0.5, "C": 0.5, "O": 0.5},
        "moral_foundations": {
            "care_harm": 0.5,
            "fairness_cheating": 0.5,
            "loyalty_betrayal": 0.5,
            "authority_subversion": 0.5,
            "sanctity_degradation": 0.5,
        },
        "drives": {"curiosity": 0.5, "autonomy": 0.5, "social_approval": 0.5},
        "epistemic_uncertainty": 0.1,
        "inner_monologue": "ok",
    },
}


def test_validate_runtime_config_none_and_no_contract():
    avatars._validate_runtime_config(None)
    avatars._validate_runtime_config({})
    avatars._validate_runtime_config({"dual_process": {}})


def test_validate_runtime_config_invalid_turn_contract(monkeypatch):
    def boom(_c):
        raise TurnContractError("bad contract")

    monkeypatch.setattr(avatars, "validate_turn_contract", boom)
    with pytest.raises(ValueError, match="bad contract"):
        avatars._validate_runtime_config({"turn_contract": {"id": "x"}})


def test_format_identity_prompt_uses_empty_msv():
    text = avatars.format_identity_prompt(
        {"name": "A", "role": "B", "description": "C", "current_msv": None}
    )
    assert "You are A" in text
    assert "{}" in text


@pytest.mark.asyncio
async def test_get_bot_identity_found_and_missing():
    row = MagicMock(role="R", description="D", baseline_msv=None, current_msv=None)
    row.name = "N"
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(fetchone=MagicMock(return_value=row)),
            MagicMock(fetchone=MagicMock(return_value=None)),
        ]
    )
    found = await avatars.get_bot_identity(conn, "bot-1")
    assert found["name"] == "N"
    assert found["baseline_msv"] == {}
    assert await avatars.get_bot_identity(conn, "missing") is None


@pytest.mark.asyncio
async def test_list_avatars_with_and_without_owner():
    r1 = MagicMock(role="R", status="available")
    r1.id = "id-1"
    r1.name = "A"
    r2 = MagicMock(role="R2", status="busy")
    r2.id = "id-2"
    r2.name = "B"
    rows = [r1, r2]
    conn = AsyncMock()
    conn.execute = AsyncMock(
        return_value=MagicMock(fetchall=MagicMock(return_value=rows))
    )

    owned = await avatars.list_avatars(conn, "owner-uuid", limit=100)
    assert len(owned) == 2
    assert owned[0]["id"] == "id-1"

    all_bots = await avatars.list_avatars(conn, None, limit=0)
    assert len(all_bots) == 2


@pytest.mark.asyncio
async def test_find_avatar_by_external_key_paths():
    row = MagicMock(role="R", baseline_msv=None, current_msv={"x": 1})
    row.id = "av-1"
    row.name = "N"
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(fetchone=MagicMock(return_value=row)),
            MagicMock(fetchone=MagicMock(return_value=None)),
            MagicMock(fetchone=MagicMock(return_value=row)),
        ]
    )

    found = await avatars.find_avatar_by_external_key(conn, "owner", "key-1")
    assert found["id"] == "av-1"
    assert found["baseline_msv"] == {}
    assert found["current_msv"] == {"x": 1}

    assert await avatars.find_avatar_by_external_key(conn, "owner", "missing") is None
    found2 = await avatars.find_avatar_by_external_key(conn, None, "key-1")
    assert found2["id"] == "av-1"


@pytest.mark.asyncio
async def test_ensure_avatar_returns_existing_or_registers(monkeypatch):
    existing = {"id": "ex-1", "name": "E"}
    monkeypatch.setattr(
        avatars,
        "find_avatar_by_external_key",
        AsyncMock(return_value=existing),
    )
    conn = AsyncMock()
    assert (
        await avatars.ensure_avatar_record(conn, None, "k", VALID_SOUL) == existing
    )

    registered = {"id": "new-1", "name": "N"}
    monkeypatch.setattr(
        avatars, "find_avatar_by_external_key", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        avatars, "register_avatar_record", AsyncMock(return_value=registered)
    )
    assert (
        await avatars.ensure_avatar_record(conn, "o", "k", VALID_SOUL, {}) == registered
    )
