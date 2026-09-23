"""Additional CLI coverage beyond pack commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cli import main


def test_memory_append_and_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    main(["memory-append", "hello episode", "--workspace", str(tmp_path)])
    assert "Appended" in capsys.readouterr().out

    out_file = tmp_path / "mem.json"
    main(["memory-export", "--workspace", str(tmp_path), "-o", str(out_file)])
    assert out_file.is_file()
    assert "Exported memory" in capsys.readouterr().out

    main(["memory-export", "--workspace", str(tmp_path)])
    data = json.loads(capsys.readouterr().out)
    assert "episodes" in data or isinstance(data, dict)


def test_memory_sync_ok_and_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"status": "success", "imported": 1}
    fail = MagicMock(status_code=422)
    fail.json.return_value = {"detail": "bad workspace"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[ok, fail])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("cli.httpx.AsyncClient", return_value=mock_client):
        main(
            [
                "memory-sync",
                "bot-1",
                "--workspace",
                str(tmp_path),
                "--kernel",
                "http://k/",
            ]
        )
        assert "imported" in capsys.readouterr().out

        with pytest.raises(SystemExit):
            main(
                [
                    "memory-sync",
                    "bot-1",
                    "--workspace",
                    str(tmp_path),
                    "--kernel",
                    "http://k",
                ]
            )


def test_pack_import_persist_true_ok_and_fail(capsys: pytest.CaptureFixture[str]):
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"id": "av-1"}
    fail = MagicMock(status_code=500)
    fail.json.return_value = {"detail": "nope"}

    with patch("cli.httpx.Client") as Client:
        client = MagicMock()
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        client.post = MagicMock(side_effect=[ok, fail])
        Client.return_value = client

        main(["pack", "import", "companion", "--persist", "true", "--kernel", "http://k"])
        assert "av-1" in capsys.readouterr().out

        with pytest.raises(SystemExit):
            main(
                ["pack", "import", "companion", "--persist", "true", "--kernel", "http://k"]
            )


def test_db_migrate_and_status(capsys: pytest.CaptureFixture[str]):
    with patch("runtime.bootstrap.init_database", new_callable=AsyncMock) as init:
        init.return_value = [1]
        main(["db", "migrate"])
        assert "Applied migrations: [1]" in capsys.readouterr().out

        init.return_value = []
        main(["db", "migrate"])
        assert "Schema up to date" in capsys.readouterr().out

    mock_conn = AsyncMock()
    connect_cm = MagicMock()
    connect_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    connect_cm.__aexit__ = AsyncMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.connect.return_value = connect_cm
    mock_engine.dispose = AsyncMock()

    with (
        patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
        patch(
            "runtime.migrations.migration_status",
            new_callable=AsyncMock,
            return_value=[
                {"version": 1, "name": "init", "applied": True},
                {"version": 2, "name": "next", "applied": False},
            ],
        ),
    ):
        main(["db", "status"])
    out = capsys.readouterr().out
    assert "001_init\tapplied" in out
    assert "002_next\tpending" in out
