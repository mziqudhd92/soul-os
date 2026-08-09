"""Pytest wrapper for dialogue turn-contract evals."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.mark.asyncio
async def test_dialogue_turn_contract_scripts():
    from importlib.util import module_from_spec, spec_from_file_location

    path = ROOT / "scripts" / "soulos-turn-contracts-eval.py"
    spec = spec_from_file_location("soulos_turn_contracts_eval", path)
    assert spec and spec.loader
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    code = await mod.main_async()
    assert code == 0
