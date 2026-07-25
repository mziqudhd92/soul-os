"""HTTP tests for SoulPacks kernel routes."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from runtime.errors import (
    PROBLEM_CONTENT_TYPE,
    SOULPACK_LICENSE_REJECTED,
    SOULPACK_NOT_FOUND,
)
from test_main import MockEmbedder, MockLLMService, mock_get_db

REPO = Path(__file__).resolve().parents[2]
PACKS = REPO / "packs" / "soulpacks"

app.dependency_overrides[get_db] = mock_get_db
app.dependency_overrides[get_embedder] = MockEmbedder
app.dependency_overrides[get_llm_service] = lambda: MockLLMService()


@pytest.fixture(autouse=True)
def _soulpacks_root(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SOULPACKS_ROOT", str(PACKS))


@pytest.mark.asyncio
async def test_list_soulpacks_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/soulpacks")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 3
    assert any(p["id"] == "support-agent" for p in body["packs"])


@pytest.mark.asyncio
async def test_list_soulpacks_q_filter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/soulpacks", params={"q": "support"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(
        "support" in p["id"]
        or "support" in p.get("name", "").lower()
        or any("support" in str(t).lower() for t in p.get("tags") or [])
        for p in body["packs"]
    )


@pytest.mark.asyncio
async def test_import_persist_false():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/avatars/import-soulpack",
            json={"pack_id": "companion", "persist": False},
        )
    assert response.status_code == 200
    body = response.json()
    assert "soul" in body
    assert body["external_key"].startswith("soulos:companion@")
    assert "baseline_msv" in body["soul"]


@pytest.mark.asyncio
async def test_import_persist_true_ensure():
    fake = {
        "id": "00000000-0000-0000-0000-000000000099",
        "name": "Luna",
        "role": "Personal Companion",
        "baseline_msv": {},
        "current_msv": {},
    }
    with patch("main.ensure_avatar_record", new_callable=AsyncMock, return_value=fake):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/v1/avatars/import-soulpack",
                json={"pack_id": "companion", "persist": True},
            )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == fake["id"]
    assert body["external_key"].startswith("soulos:")


@pytest.mark.asyncio
async def test_import_unknown_pack_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/avatars/import-soulpack",
            json={"pack_id": "nope", "persist": False},
        )
    assert response.status_code == 404
    assert PROBLEM_CONTENT_TYPE in response.headers.get("content-type", "")
    assert response.json()["code"] == SOULPACK_NOT_FOUND


@pytest.mark.asyncio
async def test_import_non_mit_422(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pack = tmp_path / "badlic"
    pack.mkdir()
    (pack / "SOUL.md").write_text("Hi.", encoding="utf-8")
    (pack / "pack.json").write_text(
        json.dumps(
            {
                "id": "badlic",
                "name": "Bad",
                "version": "1.0.0",
                "license": "GPL-3.0",
                "role": "X",
                "attachment_style": "Secure",
                "files": ["SOUL.md"],
                "baseline_msv": {
                    "hexaco": {k: 0.0 for k in "HEXACO"},
                    "moral_foundations": {
                        "care_harm": 0.5,
                        "fairness_cheating": 0.5,
                        "loyalty_betrayal": 0.5,
                        "authority_subversion": 0.5,
                        "sanctity_degradation": 0.5,
                    },
                    "drives": {
                        "curiosity": 0.5,
                        "autonomy": 0.5,
                        "social_approval": 0.5,
                    },
                    "epistemic_uncertainty": 0.1,
                    "inner_monologue": "x",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "catalog.json").write_text(
        json.dumps({"packs": [{"id": "badlic", "path": "badlic"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("SOULPACKS_ROOT", str(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/avatars/import-soulpack",
            json={"pack_id": "badlic", "persist": False},
        )
    assert response.status_code == 422
    assert response.json()["code"] == SOULPACK_LICENSE_REJECTED


@pytest.mark.asyncio
async def test_import_alias_register():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/avatars/import-soulpack",
            json={"pack_id": "dev-twin", "register": False},
        )
    assert response.status_code == 200
    assert "soul" in response.json()
