"""Tests for ClawSouls import conversion."""

from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from runtime.clawsouls_import import convert_bundle, load_local_bundle, merge_markdown
from test_main import MockEmbedder, MockLLMService, mock_get_db

app.dependency_overrides[get_db] = mock_get_db
app.dependency_overrides[get_embedder] = MockEmbedder
app.dependency_overrides[get_llm_service] = lambda: MockLLMService()

SAMPLE_BUNDLE = {
    "manifest": {
        "name": "surgical-coder",
        "displayName": "Surgical Coder 🧠",
        "version": "1.3.0",
        "description": "Precision-focused coding agent.",
        "category": "development",
        "license": "Apache-2.0",
        "tags": ["coding", "precision"],
        "files": {"soul": "SOUL.md"},
        "disclosure": {"summary": "Disciplined minimal coder."},
    },
    "files": {
        "SOUL.md": "# Surgical Coder\n\nYou make minimal, targeted changes.",
    },
}


def test_merge_markdown_from_bundle():
    text = merge_markdown(SAMPLE_BUNDLE["manifest"], SAMPLE_BUNDLE["files"])
    assert "minimal, targeted changes" in text


def test_convert_bundle_surgical_preset():
    soul, runtime, warnings = convert_bundle(SAMPLE_BUNDLE, msv_preset="surgical-coder")
    assert soul["name"] == "Surgical Coder"
    assert soul["role"] == "Development Agent"
    assert "minimal" in soul["description"]
    assert soul["baseline_msv"]["hexaco"]["C"] == 0.95
    assert runtime["source"]["type"] == "clawsouls"
    assert runtime["source"]["license"] == "Apache-2.0"
    assert "clawsouls.ai" in runtime["source"]["url"]
    assert "attribution_notice" in runtime["source"]
    assert any("MSV preset" in w for w in warnings)


def test_load_local_fixture():
    fixture = Path(__file__).parent / "fixtures" / "clawsouls" / "minimal-fixture"
    bundle = load_local_bundle(fixture)
    soul, _, _ = convert_bundle(bundle, msv_preset="minimalist")
    assert soul["attachment_style"] == "Dismissive-Avoidant"


@pytest.mark.asyncio
async def test_import_clawsouls_endpoint_convert_only():
    with patch(
        "main.import_clawsouls_soul",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.return_value = (
            {
                "name": "Test",
                "role": "Dev",
                "description": "Hello",
                "attachment_style": "Secure",
                "baseline_msv": SAMPLE_BUNDLE["manifest"],
            },
            {"source": {"type": "clawsouls"}},
            ["MSV preset applied: default"],
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/v1/avatars/import-clawsouls",
                json={
                    "owner": "clawsouls",
                    "name": "surgical-coder",
                    "register": False,
                },
            )
        assert res.status_code == 200
        body = res.json()
        assert body["soul"]["name"] == "Test"
        assert body["external_key"].startswith("clawsouls:")


@pytest.mark.asyncio
async def test_import_clawsouls_endpoint_register():
    record = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Surgical Coder",
        "role": "Development Agent",
        "baseline_msv": {},
        "current_msv": {},
    }
    with patch(
        "main.import_clawsouls_soul",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.return_value = (
            {
                "name": "Surgical Coder",
                "role": "Development Agent",
                "description": "Hi",
                "attachment_style": "Secure",
                "baseline_msv": {
                    "hexaco": {
                        "H": 0.9,
                        "E": 0.1,
                        "X": 0.2,
                        "A": 0.4,
                        "C": 0.95,
                        "O": 0.8,
                    },
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
                    "inner_monologue": "Ready",
                },
            },
            {"source": {"type": "clawsouls", "version": "1.3.0"}},
            [],
        )
        with patch("main.ensure_avatar_record", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = record
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                res = await ac.post(
                    "/v1/avatars/import-clawsouls",
                    json={
                        "owner": "clawsouls",
                        "name": "surgical-coder",
                        "register": True,
                    },
                )
            assert res.status_code == 200
            assert res.json()["id"] == record["id"]
            mock_ensure.assert_awaited_once()
