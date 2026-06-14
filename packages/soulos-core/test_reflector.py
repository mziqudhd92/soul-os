import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soul_validation import default_msv_dict


@pytest.mark.asyncio
async def test_reflector_uses_own_connection_not_shared_db():
    from runtime.reflector import run_system_2_reflector

    shared_db = AsyncMock()
    shared_db.commit = AsyncMock()
    current_msv = default_msv_dict()
    new_msv = {**current_msv, "epistemic_uncertainty": 0.42}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": json.dumps(new_msv)}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mock_conn = AsyncMock()

    class MockRow:
        baseline_msv = current_msv
        cognitive_meta = {}

    class MockResult:
        def fetchone(self):
            return MockRow()

    mock_conn.execute = AsyncMock(return_value=MockResult())
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("runtime.reflector.httpx.AsyncClient", return_value=mock_client),
        patch("runtime.reflector.engine") as mock_engine,
    ):
        mock_engine.begin.return_value = mock_begin_ctx
        result = await run_system_2_reflector("bot-1", "hello", current_msv)

    assert result.msv["epistemic_uncertainty"] == 0.42
    mock_engine.begin.assert_called_once()
    assert mock_conn.execute.await_count >= 1
    shared_db.commit.assert_not_awaited()
    shared_db.execute.assert_not_awaited()
