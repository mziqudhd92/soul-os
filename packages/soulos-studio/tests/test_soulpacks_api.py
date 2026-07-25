"""Studio proxy tests for SoulPacks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from soulos_studio.app import app


@pytest.mark.asyncio
async def test_api_soulpacks_list_proxies_kernel():
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "packs": [{"id": "support-agent", "name": "Site Support", "version": "1.0.0"}],
        "total": 1,
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_res)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/soulpacks", params={"q": "support"})

    assert response.status_code == 200
    assert response.json()["packs"][0]["id"] == "support-agent"
    mock_client.get.assert_awaited()


@pytest.mark.asyncio
async def test_api_soulpacks_import_proxies_kernel():
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "soul": {"name": "Luna", "baseline_msv": {"hexaco": {}}},
        "external_key": "soulos:companion@1.0.0",
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_res)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/soulpacks/import",
                json={"pack_id": "companion", "persist": False},
            )

    assert response.status_code == 200
    assert response.json()["external_key"].startswith("soulos:")
    mock_client.post.assert_awaited()


def test_index_has_soulpacks_nav():
    from pathlib import Path

    html = (
        Path(__file__).resolve().parents[1]
        / "soulos_studio"
        / "static"
        / "index.html"
    ).read_text(encoding="utf-8")
    assert "nav-soulpacks" in html
    assert "SoulPacks" in html
