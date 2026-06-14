"""Build cognitive_state SSE payloads for dual-process telemetry."""

from __future__ import annotations

import json
import time
from typing import Any


DEFAULT_SYSTEM1_THRESHOLD = 0.35
DEFAULT_SYSTEM2_MAX_LOOPS = 3


def default_runtime_config() -> dict[str, Any]:
    return {
        "dual_process": {
            "system1_threshold": DEFAULT_SYSTEM1_THRESHOLD,
            "system2_max_loops": DEFAULT_SYSTEM2_MAX_LOOPS,
        }
    }


def merge_runtime_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = default_runtime_config()
    if not raw:
        return base
    dual = dict(base["dual_process"])
    if isinstance(raw.get("dual_process"), dict):
        dual.update(raw["dual_process"])
    if isinstance(raw.get("engine"), dict):
        base["engine"] = raw["engine"]
    base["dual_process"] = dual
    return base


def system1_threshold(runtime_config: dict[str, Any] | None) -> float:
    cfg = merge_runtime_config(runtime_config)
    return float(cfg["dual_process"]["system1_threshold"])


def confidence_from_msv(current_msv: dict[str, Any]) -> float:
    uncertainty = float(current_msv.get("epistemic_uncertainty", 0.1))
    return max(0.0, min(1.0, 1.0 - uncertainty))


def build_cognitive_state(
    current_path: str,
    system_1: dict[str, Any] | None = None,
    system_2: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": int(time.time()),
        "current_path": current_path,
    }
    if system_1 is not None:
        payload["system_1"] = system_1
    if system_2 is not None:
        payload["system_2"] = system_2
    return payload


def format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def format_cognitive_state_sse(
    current_path: str,
    system_1: dict[str, Any] | None = None,
    system_2: dict[str, Any] | None = None,
) -> str:
    return format_sse(
        "cognitive_state",
        build_cognitive_state(current_path, system_1=system_1, system_2=system_2),
    )
