"""Unit tests for ChatPipeline (load helpers + SSE generate stream)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runtime.pipeline import ChatPipeline
from runtime.reflector import ReflectorResult
from soul_validation import default_msv_dict


class _Row:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Db:
    def __init__(self, row):
        self._row = row

    async def execute(self, query, params=None):
        return _Result(self._row)


@pytest.mark.asyncio
async def test_load_current_msv_default_when_missing():
    pipeline = ChatPipeline()
    msv = await pipeline.load_current_msv(_Db(None), "bot-1")
    assert msv == default_msv_dict()


@pytest.mark.asyncio
async def test_load_current_msv_dict_and_json_string():
    pipeline = ChatPipeline()
    payload = default_msv_dict()
    payload["epistemic_uncertainty"] = 0.33

    as_dict = await pipeline.load_current_msv(
        _Db(_Row(current_msv=payload)), "bot-1"
    )
    assert as_dict["epistemic_uncertainty"] == 0.33

    as_str = await pipeline.load_current_msv(
        _Db(_Row(current_msv=json.dumps(payload))), "bot-1"
    )
    assert as_str["epistemic_uncertainty"] == 0.33


@pytest.mark.asyncio
async def test_load_current_msv_empty_falsy_returns_default():
    pipeline = ChatPipeline()
    msv = await pipeline.load_current_msv(
        _Db(_Row(current_msv=None)), "bot-1"
    )
    assert msv == default_msv_dict()


@pytest.mark.asyncio
async def test_load_runtime_config_json_string_and_none():
    pipeline = ChatPipeline()
    raw = {"dual_process": {"system1_threshold": 0.55}}
    cfg = await pipeline.load_runtime_config(
        _Db(_Row(runtime_config=json.dumps(raw))), "bot-1"
    )
    assert cfg["dual_process"]["system1_threshold"] == 0.55

    default_cfg = await pipeline.load_runtime_config(_Db(None), "bot-1")
    assert "dual_process" in default_cfg


def _stream_client(lines: list[str], status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code

    async def aiter_lines():
        for line in lines:
            yield line

    response.aiter_lines = aiter_lines
    stream_cm = MagicMock()
    stream_cm.__aenter__ = AsyncMock(return_value=response)
    stream_cm.__aexit__ = AsyncMock(return_value=False)

    client = MagicMock()
    client.stream.return_value = stream_cm
    client_cm = MagicMock()
    client_cm.__aenter__ = AsyncMock(return_value=client)
    client_cm.__aexit__ = AsyncMock(return_value=False)
    return client_cm


@pytest.mark.asyncio
async def test_generate_chat_stream_success_with_context_and_reflector_after():
    pipeline = ChatPipeline()
    msv = default_msv_dict()
    reflector = ReflectorResult(
        msv={**msv, "epistemic_uncertainty": 0.2},
        latency_ms=12,
        reasoning_tokens=5,
        loop_count=1,
        active_mcp_tools=["retrieve_memory"],
    )

    async def slow_reflector(*_a, **_k):
        return reflector

    db = _Db(
        _Row(
            current_msv=msv,
            runtime_config={"dual_process": {"system1_threshold": 0.35}},
        )
    )
    lines = [
        "",
        "not-json",
        json.dumps({"other": 1}),
        json.dumps({"response": "Hi"}),
        json.dumps({"response": " there"}),
    ]

    with (
        patch("runtime.pipeline.httpx.AsyncClient", return_value=_stream_client(lines)),
        patch("runtime.pipeline.run_system_2_reflector", side_effect=slow_reflector),
    ):
        events = []
        async for chunk in pipeline.generate_chat_stream(
            "bot-1", "hello", ["mem-a"], db
        ):
            events.append(chunk)

    joined = "".join(events)
    assert "cognitive_state" in joined
    assert "message" in joined
    assert "msv_update" in joined
    assert "Hi" in joined


@pytest.mark.asyncio
async def test_generate_chat_stream_low_confidence_and_error_status():
    pipeline = ChatPipeline()
    msv = default_msv_dict()
    msv["epistemic_uncertainty"] = 0.9  # confidence 0.1 < threshold

    async def immediate_reflector(*_a, **_k):
        return ReflectorResult(msv=msv, latency_ms=1, reasoning_tokens=0)

    db = _Db(
        _Row(
            current_msv=msv,
            runtime_config={"dual_process": {"system1_threshold": 0.5}},
        )
    )

    with (
        patch(
            "runtime.pipeline.httpx.AsyncClient",
            return_value=_stream_client([], status_code=500),
        ),
        patch("runtime.pipeline.run_system_2_reflector", side_effect=immediate_reflector),
    ):
        events = []
        async for chunk in pipeline.generate_chat_stream("bot-1", "hello", [], db):
            events.append(chunk)

    joined = "".join(events)
    assert "system_2_deliberation" in joined
    assert "Failed to generate" in joined


@pytest.mark.asyncio
async def test_generate_chat_stream_reflector_during_tokens():
    pipeline = ChatPipeline()
    msv = default_msv_dict()
    done_result = ReflectorResult(
        msv=msv, latency_ms=3, reasoning_tokens=2, active_mcp_tools=[]
    )

    db = _Db(_Row(current_msv=msv, runtime_config={}))
    lines = [
        json.dumps({"response": "A"}),
        json.dumps({"response": "B"}),
    ]

    # Pre-completed future so reflector_task.done() is True on first token
    done_future = asyncio.get_running_loop().create_future()
    done_future.set_result(done_result)

    def fake_create_task(coro):
        coro.close()
        return done_future

    with (
        patch("runtime.pipeline.httpx.AsyncClient", return_value=_stream_client(lines)),
        patch("runtime.pipeline.asyncio.create_task", side_effect=fake_create_task),
    ):
        events = []
        async for chunk in pipeline.generate_chat_stream("bot-1", "hi", [], db):
            events.append(chunk)

    joined = "".join(events)
    assert "msv_update" in joined
    assert "system_2_deliberation" in joined
