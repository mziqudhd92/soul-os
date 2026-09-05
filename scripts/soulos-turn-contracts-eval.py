#!/usr/bin/env python3
"""Dialogue eval runner for turn contracts (in-process ASGI, no live LLM)."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "packages" / "soulos-core"
sys.path.insert(0, str(CORE))

from httpx import ASGITransport, AsyncClient  # noqa: E402

from dependencies import get_db, get_embedder, get_llm_service  # noqa: E402
from main import app  # noqa: E402
from test_main import MockEmbedder, MockLLMService, mock_get_db  # noqa: E402

FIXTURE_DIR = CORE / "testdata" / "turn_contracts"
BOT_ID = "123e4567-e89b-12d3-a456-426614174000"
SCRIPTS = [
    "quiet.json",
    "octoner.json",
    "try_everything.json",
    "backtrack.json",
    "retry_idempotency.json",
    "expired_session.json",
]


class ContractLLM(MockLLMService):
    def __init__(self, contract: dict[str, Any]):
        self._contract = contract

    async def load_runtime_config(self, db, bot_id: str) -> dict:
        return {"turn_contract": self._contract}


_STORE: dict[tuple[str, str], dict[str, Any]] = {}
_VERSIONS: dict[str, int] = {}


async def _mem_get(db, bot_id: str, session_id: str):
    row = _STORE.get((bot_id, session_id))
    return deepcopy(row) if row else None


async def _mem_advance(
    db,
    *,
    bot_id: str,
    session_id: str,
    expected_version: int,
    current_step: str,
    slots: dict,
    turn_version: int,
    last_idempotency_key: str | None = None,
    last_success_response: dict | None = None,
):
    row = _STORE.get((bot_id, session_id))
    if not row or row["turn_version"] != expected_version:
        return False
    row["current_step"] = current_step
    row["slots"] = deepcopy(slots)
    row["turn_version"] = turn_version
    if last_idempotency_key is not None:
        row["last_idempotency_key"] = last_idempotency_key
    if last_success_response is not None:
        row["last_success_response"] = deepcopy(last_success_response)
    _VERSIONS[session_id] = turn_version
    return True


async def _mem_store_success(
    db,
    *,
    bot_id: str,
    session_id: str,
    turn_version: int,
    last_idempotency_key: str | None,
    last_success_response: dict,
):
    row = _STORE.get((bot_id, session_id))
    if not row or row["turn_version"] != turn_version:
        return
    if last_idempotency_key is not None:
        row["last_idempotency_key"] = last_idempotency_key
    row["last_success_response"] = deepcopy(last_success_response)


async def _mem_ensure(db, *, bot_id: str, session_id: str, initial_step: str):
    existing = await _mem_get(db, bot_id, session_id)
    if existing:
        return existing
    _STORE[(bot_id, session_id)] = {
        "current_step": initial_step,
        "slots": {},
        "turn_version": 0,
        "last_idempotency_key": None,
        "last_success_response": None,
    }
    _VERSIONS[session_id] = 0
    return await _mem_get(db, bot_id, session_id)


async def run_script(path: Path) -> list[str]:
    errors: list[str] = []
    script = json.loads(path.read_text(encoding="utf-8"))
    contract = json.loads((FIXTURE_DIR / script["contract"]).read_text(encoding="utf-8"))
    _STORE.clear()
    _VERSIONS.clear()

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_embedder] = MockEmbedder
    app.dependency_overrides[get_llm_service] = lambda: ContractLLM(contract)

    patches = [
        patch("routes.hybrid.ensure_turn_session", _mem_ensure),
        patch("runtime.hybrid_complete.get_turn_session", _mem_get),
        patch("runtime.hybrid_complete.advance_turn_session", _mem_advance),
        patch("routes.hybrid.store_turn_success_response", _mem_store_success),
    ]
    for p in patches:
        p.start()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            for i, turn in enumerate(script["turns"]):
                sid = turn["session_id"]
                action = turn["action"]
                if action == "prepare":
                    resp = await ac.post(
                        "/hybrid/prepare",
                        json={
                            "bot_id": BOT_ID,
                            "query": turn.get("query", ""),
                            "session_id": sid,
                        },
                    )
                    if resp.status_code != 200:
                        errors.append(f"{path.name}[{i}] prepare status {resp.status_code}")
                        continue
                    ctx = resp.json().get("contract_context") or {}
                    _VERSIONS[sid] = ctx.get("turn_version", 0)
                    if turn.get("expect_step") and ctx.get("expected_step") != turn["expect_step"]:
                        errors.append(
                            f"{path.name}[{i}] step {ctx.get('expected_step')} != {turn['expect_step']}"
                        )
                    if (
                        "expect_version" in turn
                        and ctx.get("turn_version") != turn["expect_version"]
                    ):
                        errors.append(
                            f"{path.name}[{i}] version {ctx.get('turn_version')} != {turn['expect_version']}"
                        )
                    continue

                if action != "complete":
                    errors.append(f"{path.name}[{i}] unknown action {action}")
                    continue

                version = turn.get("expected_version_override")
                if version is None:
                    version = _VERSIONS.get(sid, 0)
                body: dict[str, Any] = {
                    "bot_id": BOT_ID,
                    "summary": turn.get("summary", ""),
                    "session_id": sid,
                    "reflect": False,
                    "filled_slots": turn.get("filled_slots"),
                    "intent": turn.get("intent"),
                    "assistant_text": turn.get("assistant_text"),
                    "expected_version": version,
                    "idempotency_key": turn.get("idempotency_key"),
                    "advance": turn.get("advance", True),
                }
                resp = await ac.post("/hybrid/complete", json=body)
                expect = turn.get("expect", "allow")
                if expect == "allow":
                    if resp.status_code not in (200, 202):
                        errors.append(
                            f"{path.name}[{i}] expected allow got {resp.status_code} {resp.text}"
                        )
                        continue
                    data = resp.json()
                    turn_info = data.get("turn") or {}
                    if turn.get("expect_step") and turn_info.get("step") != turn["expect_step"]:
                        errors.append(
                            f"{path.name}[{i}] step {turn_info.get('step')} != {turn['expect_step']}"
                        )
                    if "expect_version" in turn and turn_info.get("turn_version") != turn["expect_version"]:
                        errors.append(
                            f"{path.name}[{i}] version {turn_info.get('turn_version')} != {turn['expect_version']}"
                        )
                    for absent in turn.get("expect_slots_absent") or []:
                        if absent in (turn_info.get("slots") or {}):
                            errors.append(f"{path.name}[{i}] slot {absent} should be cleared")
                    if turn_info.get("turn_version") is not None:
                        _VERSIONS[sid] = turn_info["turn_version"]
                else:
                    want_status = turn.get("expect_status", 422)
                    if resp.status_code != want_status:
                        # 409 vs 422 vs 404
                        if turn.get("expect_code") == "TURN_SESSION_EXPIRED":
                            want_status = 404
                        if turn.get("expect_code") == "TURN_STATE_STALE":
                            want_status = 409
                        if resp.status_code != want_status and resp.status_code not in (404, 409, 422):
                            errors.append(
                                f"{path.name}[{i}] expected deny status, got {resp.status_code}"
                            )
                    problem = resp.json()
                    code = problem.get("code")
                    if turn.get("expect_code") and code != turn["expect_code"]:
                        errors.append(
                            f"{path.name}[{i}] code {code} != {turn['expect_code']}"
                        )
    finally:
        for p in patches:
            p.stop()
        app.dependency_overrides[get_llm_service] = lambda: MockLLMService()
        _STORE.clear()
    return errors


async def main_async() -> int:
    all_errors: list[str] = []
    for name in SCRIPTS:
        path = FIXTURE_DIR / name
        if not path.exists():
            all_errors.append(f"missing script {name}")
            continue
        all_errors.extend(await run_script(path))
    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("soulos-turn-contracts: OK")
    return 0


def main() -> int:
    import asyncio

    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
