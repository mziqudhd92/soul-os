"""Dry-run test for examples/soulpack-sidecar/seed_soulpack.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "examples" / "soulpack-sidecar" / "seed_soulpack.py"


def _load_seed():
    spec = importlib.util.spec_from_file_location("seed_soulpack", SEED)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_seed_script_dry_run():
    mod = _load_seed()
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "soul": {"name": "Site Support"},
        "external_key": "soulos:support-agent@1.0.0",
    }
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.post = MagicMock(return_value=mock_res)

    with patch.object(mod.httpx, "Client", return_value=mock_client):
        code = mod.main(
            ["--pack-id", "support-agent", "--persist", "false", "--kernel", "http://x"]
        )
    assert code == 0
    mock_client.post.assert_called_once()
    body = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get(
        "json"
    )
    if body is None:
        body = mock_client.post.call_args[0][1] if len(mock_client.post.call_args[0]) > 1 else None
    # httpx Client.post(url, json=payload)
    assert mock_client.post.call_args.kwargs["json"]["persist"] is False
