"""ASGI route tests for SoulOS Studio app."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from soulos_studio.app import app
from soulos_studio.soul_form import default_form


def _valid_form() -> dict:
    return default_form()


def _mock_http_client(*, get=None, post=None, stream=None):
    client = AsyncMock()
    if get is not None:
        client.get = AsyncMock(return_value=get)
    if post is not None:
        client.post = AsyncMock(return_value=post)
    if stream is not None:
        client.stream = stream
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_index(client):
    res = await client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert b"SoulOS" in res.content or b"soul" in res.content.lower()


@pytest.mark.asyncio
async def test_meta_and_defaults(client):
    meta = await client.get("/api/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert "hexaco_labels" in body
    assert "attachment_styles" in body
    assert body["kernel_url"]

    defaults = await client.get("/api/defaults")
    assert defaults.status_code == 200
    assert defaults.json()["name"] == "My Avatar"


@pytest.mark.asyncio
async def test_build_soul_ok(client):
    res = await client.post("/api/build", json=_valid_form())
    assert res.status_code == 200
    assert res.json()["name"] == "My Avatar"
    assert "baseline_msv" in res.json()


@pytest.mark.asyncio
async def test_build_soul_validation_error(client):
    form = _valid_form()
    form["hexaco"] = {"H": 99.0}  # out of schema range / incomplete
    # Force invalid by wiping required hexaco keys after build path —
    # send soul via validate instead; for build we need schema failure.
    form["attachment_style"] = "NotARealStyle"
    res = await client.post("/api/build", json=form)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_build_soul_text(client):
    res = await client.post("/api/build-soul", json=_valid_form())
    assert res.status_code == 200
    assert res.json()["text"].startswith("---")


@pytest.mark.asyncio
async def test_import_text_ok(client):
    build = await client.post("/api/build-soul", json=_valid_form())
    text = build.json()["text"]
    res = await client.post("/api/import-text", json={"text": text})
    assert res.status_code == 200
    assert "form" in res.json()
    assert "soul" in res.json()


@pytest.mark.asyncio
async def test_import_text_invalid(client):
    res = await client.post("/api/import-text", json={"text": "not a soul"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_validate_ok_and_error(client):
    built = await client.post("/api/build", json=_valid_form())
    soul = built.json()
    ok = await client.post("/api/validate", json={"soul": soul})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True

    bad = await client.post("/api/validate", json={"soul": {"name": "x"}})
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_import_soul_ok_and_error(client):
    built = await client.post("/api/build", json=_valid_form())
    soul = built.json()
    ok = await client.post("/api/import", json={"soul": soul})
    assert ok.status_code == 200
    assert ok.json()["form"]["name"] == soul["name"]

    # Parses into a form but fails schema validation on rebuild
    bad = await client.post(
        "/api/import",
        json={"soul": {"name": "x", "baseline_msv": {"hexaco": {"H": "not-a-float"}}}},
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_register_validation_error(client):
    res = await client.post("/api/register", json={"soul": {"name": "x"}})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_kernel_unreachable(client):
    built = await client.post("/api/build", json=_valid_form())
    soul = built.json()
    with patch(
        "soulos_studio.app.httpx.AsyncClient",
        side_effect=httpx.RequestError("down", request=MagicMock()),
    ):
        # RequestError is raised on enter/post — patch post path via client mock
        pass

    mock_client = _mock_http_client()
    mock_client.post = AsyncMock(side_effect=httpx.RequestError("down", request=MagicMock()))
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post("/api/register", json={"soul": soul})
    assert res.status_code == 502
    assert "Kernel unreachable" in res.json()["detail"]


@pytest.mark.asyncio
async def test_register_kernel_error_status(client):
    built = await client.post("/api/build", json=_valid_form())
    soul = built.json()
    mock_res = MagicMock()
    mock_res.status_code = 400
    mock_res.json.return_value = {"detail": "bad soul"}
    mock_client = _mock_http_client(post=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post("/api/register", json={"soul": soul})
    assert res.status_code == 400
    assert res.json()["detail"] == "bad soul"


@pytest.mark.asyncio
async def test_register_ok(client):
    built = await client.post("/api/build", json=_valid_form())
    soul = built.json()
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"id": "av-1", "name": soul["name"]}
    mock_client = _mock_http_client(post=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post("/api/register", json={"soul": soul})
    assert res.status_code == 200
    assert res.json()["id"] == "av-1"


@pytest.mark.asyncio
async def test_docs_catalog_and_content(client):
    catalog = await client.get("/api/docs/catalog")
    assert catalog.status_code == 200
    assert "sections" in catalog.json()

    content = await client.get(
        "/api/docs/content", params={"path": "getting-started/quickstart.md"}
    )
    assert content.status_code == 200
    assert "html" in content.json()

    missing = await client.get("/api/docs/content", params={"path": "../etc/passwd"})
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_kernel_health_ok(client):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"service": "soulos-core"}
    mock_client = _mock_http_client(get=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.get("/api/kernel-health")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["service"] == "soulos-core"


@pytest.mark.asyncio
async def test_kernel_health_bad_status(client):
    mock_res = MagicMock()
    mock_res.status_code = 503
    mock_client = _mock_http_client(get=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.get("/api/kernel-health")
    assert res.json()["ok"] is False
    assert "503" in res.json()["detail"]


@pytest.mark.asyncio
async def test_kernel_health_unreachable(client):
    mock_client = _mock_http_client()
    mock_client.get = AsyncMock(
        side_effect=httpx.RequestError("refused", request=MagicMock())
    )
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.get("/api/kernel-health")
    assert res.json()["ok"] is False


@pytest.mark.asyncio
async def test_tutorials_list_and_content(client):
    listing = await client.get("/api/tutorials")
    assert listing.status_code == 200
    assert len(listing.json()["tutorials"]) >= 5

    doc = await client.get("/api/tutorials/first-soul")
    assert doc.status_code == 200
    assert "html" in doc.json() or "title" in doc.json()

    missing = await client.get("/api/tutorials/does-not-exist")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_soulpacks_list_unreachable(client):
    mock_client = _mock_http_client()
    mock_client.get = AsyncMock(
        side_effect=httpx.RequestError("down", request=MagicMock())
    )
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.get("/api/soulpacks")
    assert res.status_code == 502


@pytest.mark.asyncio
async def test_soulpacks_list_error_status(client):
    mock_res = MagicMock()
    mock_res.status_code = 500
    mock_res.text = "boom"
    mock_client = _mock_http_client(get=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.get("/api/soulpacks")
    assert res.status_code == 500


@pytest.mark.asyncio
async def test_soulpacks_import_unreachable(client):
    mock_client = _mock_http_client()
    mock_client.post = AsyncMock(
        side_effect=httpx.RequestError("down", request=MagicMock())
    )
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            "/api/soulpacks/import", json={"pack_id": "x", "persist": False}
        )
    assert res.status_code == 502


@pytest.mark.asyncio
async def test_soulpacks_import_error_status(client):
    mock_res = MagicMock()
    mock_res.status_code = 404
    mock_res.json.return_value = {"detail": "not found"}
    mock_client = _mock_http_client(post=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            "/api/soulpacks/import", json={"pack_id": "missing", "persist": False}
        )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_hybrid_prepare_ok(client):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"memories": [], "session_id": "s1"}
    mock_client = _mock_http_client(post=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            "/api/hybrid/prepare",
            json={"avatar_id": "a1", "query": "hello", "top_k": 3},
        )
    assert res.status_code == 200
    assert res.json()["query"] == "hello"
    assert res.json()["session_id"] == "s1"


@pytest.mark.asyncio
async def test_hybrid_prepare_unreachable(client):
    mock_client = _mock_http_client()
    mock_client.post = AsyncMock(
        side_effect=httpx.RequestError("down", request=MagicMock())
    )
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            "/api/hybrid/prepare",
            json={"avatar_id": "a1", "query": "hello"},
        )
    assert res.status_code == 502


@pytest.mark.asyncio
async def test_hybrid_prepare_error_status(client):
    mock_res = MagicMock()
    mock_res.status_code = 400
    mock_res.json.return_value = {"detail": "bad"}
    mock_client = _mock_http_client(post=mock_res)
    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            "/api/hybrid/prepare",
            json={"avatar_id": "a1", "query": "hello"},
        )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_chat_stream_ok(client):
    async def aiter_bytes():
        yield b"data: hello\n\n"

    mock_response = MagicMock()
    mock_response.aiter_bytes = aiter_bytes
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            "/api/chat", json={"avatar_id": "a1", "message": "hi"}
        )
    assert res.status_code == 200
    assert b"hello" in res.content


@pytest.mark.asyncio
async def test_chat_stream_unreachable(client):
    mock_client = AsyncMock()
    mock_client.stream = MagicMock(
        side_effect=httpx.RequestError("down", request=MagicMock())
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("soulos_studio.app.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            "/api/chat", json={"avatar_id": "a1", "message": "hi"}
        )
    assert res.status_code == 200
    assert b"Kernel unreachable" in res.content
