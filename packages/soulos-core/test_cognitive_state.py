"""Tests for cognitive_state SSE telemetry (Phase 2)."""

import json

import pytest

from runtime.cognitive_telemetry import (
    build_cognitive_state,
    confidence_from_msv,
    format_cognitive_state_sse,
    merge_runtime_config,
    system1_threshold,
)
from runtime.pipeline import ChatPipeline


def test_confidence_from_msv():
    assert confidence_from_msv({"epistemic_uncertainty": 0.1}) == 0.9
    assert confidence_from_msv({"epistemic_uncertainty": 0.0}) == 1.0


def test_system1_threshold_from_runtime_config():
    cfg = merge_runtime_config({"dual_process": {"system1_threshold": 0.42}})
    assert system1_threshold(cfg) == 0.42


def test_cognitive_state_sse_format():
    line = format_cognitive_state_sse(
        "system_1_heuristic",
        system_1={
            "confidence_score": 0.21,
            "cached_response_triggered": False,
            "latency_ms": 45,
        },
    )
    assert line.startswith("event: cognitive_state\n")
    data = json.loads(line.split("data: ", 1)[1].strip())
    assert data["current_path"] == "system_1_heuristic"
    assert data["system_1"]["confidence_score"] == 0.21


@pytest.mark.asyncio
async def test_pipeline_load_runtime_config():
    class MockRow:
        def __init__(self, runtime_config):
            self.runtime_config = runtime_config

    class MockResult:
        def fetchone(self):
            return MockRow({"dual_process": {"system1_threshold": 0.42}})

    class MockDb:
        async def execute(self, query, params=None):
            return MockResult()

    pipeline = ChatPipeline()
    runtime = await pipeline.load_runtime_config(MockDb(), "bot-id")
    assert runtime["dual_process"]["system1_threshold"] == 0.42
