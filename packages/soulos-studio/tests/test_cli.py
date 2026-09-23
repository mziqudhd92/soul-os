"""CLI entrypoint tests."""

from unittest.mock import patch

from soulos_studio.cli import main


def test_cli_main_sets_kernel_and_runs_uvicorn(monkeypatch):
    monkeypatch.delenv("SOULOS_KERNEL_URL", raising=False)
    with patch("uvicorn.run") as run:
        with patch(
            "sys.argv",
            [
                "soulos-studio",
                "--host",
                "0.0.0.0",
                "--port",
                "9999",
                "--kernel",
                "http://k:8000/",
            ],
        ):
            main()
    assert run.call_args.args[0] == "soulos_studio.app:app"
    assert run.call_args.kwargs["host"] == "0.0.0.0"
    assert run.call_args.kwargs["port"] == 9999
    import os

    assert os.environ["SOULOS_KERNEL_URL"] == "http://k:8000"
