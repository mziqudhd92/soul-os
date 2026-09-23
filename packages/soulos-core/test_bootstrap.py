"""Unit tests for runtime.bootstrap (DB migrate + Ollama warmup)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from runtime import bootstrap


@pytest.mark.asyncio
async def test_init_database_applies_and_up_to_date():
    mock_conn = AsyncMock()
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    begin_cm.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.begin.return_value = begin_cm
    mock_engine.dispose = AsyncMock()

    with (
        patch("runtime.bootstrap.create_async_engine", return_value=mock_engine),
        patch("runtime.bootstrap.apply_migrations", new_callable=AsyncMock) as apply,
    ):
        apply.return_value = [1, 2]
        applied = await bootstrap.init_database("postgresql+asyncpg://x/y")
        assert applied == [1, 2]

        apply.return_value = []
        applied2 = await bootstrap.init_database("postgresql+asyncpg://x/y")
        assert applied2 == []

    assert mock_engine.dispose.await_count == 2


@pytest.mark.asyncio
async def test_wait_for_ollama_success():
    mock_resp = MagicMock(status_code=200)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("runtime.bootstrap.httpx.AsyncClient", return_value=mock_client):
        assert await bootstrap.wait_for_ollama() is True


@pytest.mark.asyncio
async def test_wait_for_ollama_retries_then_succeeds():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[
            httpx.RequestError("down"),
            MagicMock(status_code=503),
            MagicMock(status_code=200),
        ]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("runtime.bootstrap.httpx.AsyncClient", return_value=mock_client),
        patch("runtime.bootstrap.asyncio.sleep", new_callable=AsyncMock),
    ):
        assert await bootstrap.wait_for_ollama() is True
    assert mock_client.get.await_count == 3


@pytest.mark.asyncio
async def test_wait_for_ollama_timeout():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("down"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("runtime.bootstrap.httpx.AsyncClient", return_value=mock_client),
        patch("runtime.bootstrap.asyncio.sleep", new_callable=AsyncMock),
    ):
        with pytest.raises(RuntimeError, match="failed to start"):
            await bootstrap.wait_for_ollama()


@pytest.mark.asyncio
async def test_pull_model_ok_and_fail():
    ok_resp = MagicMock(status_code=200, text="ok")
    fail_resp = MagicMock(status_code=500, text="boom")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[ok_resp, fail_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("runtime.bootstrap.httpx.AsyncClient", return_value=mock_client):
        await bootstrap.pull_model("tiny")
        await bootstrap.pull_model("tiny")

    assert mock_client.post.await_count == 2
