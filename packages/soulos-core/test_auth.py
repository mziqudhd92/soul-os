import secrets

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from auth import resolve_account_context
from config import GATEWAY_SECRET, validate_gateway_secret


def test_resolve_account_open_mode_without_headers():
    ctx = resolve_account_context(None, None)
    assert ctx.account_id is None


def test_resolve_account_open_mode_with_trusted_headers():
    ctx = resolve_account_context("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", GATEWAY_SECRET)
    assert ctx.account_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_resolve_account_rejects_wrong_secret_with_compare_digest():
    ctx = resolve_account_context(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "wrong-secret-value"
    )
    assert ctx.account_id is None


def test_resolve_account_accepts_matching_secret_with_compare_digest():
    ctx = resolve_account_context(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", GATEWAY_SECRET
    )
    assert ctx.account_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_validate_gateway_secret_rejects_weak_value_in_cloud_mode(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", True)
    monkeypatch.setattr("config.GATEWAY_SECRET", "changeme_gateway_secret")
    with pytest.raises(RuntimeError, match="weak default"):
        validate_gateway_secret()


def test_validate_gateway_secret_allows_strong_value_in_cloud_mode(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", True)
    monkeypatch.setattr(
        "config.GATEWAY_SECRET", secrets.token_urlsafe(32)
    )
    validate_gateway_secret()


def test_resolve_account_cloud_mode_requires_gateway(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", True)
    with pytest.raises(HTTPException) as exc:
        resolve_account_context(None, None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_cloud_mode_rejects_direct_kernel_access(monkeypatch):
    monkeypatch.setattr("config.REQUIRE_AUTH", True)

    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/avatars", json={"name": "x"})
    assert response.status_code == 401
