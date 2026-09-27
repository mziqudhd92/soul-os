"""Feature-based System 1 / System 2 routing with async decision logging."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config import DEFAULT_UNCERTAINTY_TRIGGER, SOULOS_ROUTER_LOG_PATH
from runtime.cognitive_telemetry import confidence_from_msv, system1_threshold

logger = logging.getLogger(__name__)

_router_queue: asyncio.Queue | None = None
_router_worker_started = False


@dataclass
class DualProcessFeatures:
    confidence: float
    retrieval_weak: bool = False
    query_complex: bool = False
    contract_incomplete: bool = False
    epistemic_uncertainty: float = 0.1
    best_distance: float | None = None


def estimate_query_complex(query: str) -> bool:
    q = (query or "").strip()
    if len(q) >= 160:
        return True
    if q.count("?") >= 2:
        return True
    if q.count(",") >= 3 or q.count(";") >= 1:
        return True
    return False


def score_system1(features: DualProcessFeatures) -> float:
    """Higher score → prefer System 1 (skip reflect)."""
    score = float(features.confidence)
    if features.retrieval_weak:
        score -= 0.25
    if features.query_complex:
        score -= 0.15
    if features.contract_incomplete:
        score -= 0.2
    return max(0.0, min(1.0, score))


def uncertainty_trigger(runtime_config: dict[str, Any] | None) -> float:
    dual = (runtime_config or {}).get("dual_process") or {}
    if isinstance(dual, dict) and dual.get("uncertainty_trigger") is not None:
        try:
            return float(dual["uncertainty_trigger"])
        except (TypeError, ValueError):
            pass
    return DEFAULT_UNCERTAINTY_TRIGGER


def system2_max_loops(runtime_config: dict[str, Any] | None) -> int:
    dual = (runtime_config or {}).get("dual_process") or {}
    if isinstance(dual, dict) and dual.get("system2_max_loops") is not None:
        try:
            return max(1, int(dual["system2_max_loops"]))
        except (TypeError, ValueError):
            pass
    return 3


def should_run_system_2(
    features: DualProcessFeatures,
    *,
    threshold: float,
    uncertainty_trigger_value: float = DEFAULT_UNCERTAINTY_TRIGGER,
    reflect_force: bool = False,
) -> bool:
    if reflect_force:
        return True
    if features.epistemic_uncertainty >= uncertainty_trigger_value:
        return True
    if features.contract_incomplete:
        return True
    return score_system1(features) < threshold


def features_from_msv(
    current_msv: dict[str, Any],
    *,
    query: str = "",
    retrieval_weak: bool = False,
    best_distance: float | None = None,
    contract_incomplete: bool = False,
) -> DualProcessFeatures:
    return DualProcessFeatures(
        confidence=confidence_from_msv(current_msv),
        retrieval_weak=retrieval_weak,
        query_complex=estimate_query_complex(query),
        contract_incomplete=contract_incomplete,
        epistemic_uncertainty=float(current_msv.get("epistemic_uncertainty", 0.1)),
        best_distance=best_distance,
    )


async def _router_log_worker(queue: asyncio.Queue) -> None:
    path = Path(SOULOS_ROUTER_LOG_PATH)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("Router log path unavailable: %s", e)
        return
    while True:
        record = await queue.get()
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("Router log write failed: %s", e)
        finally:
            queue.task_done()


def _ensure_router_worker() -> asyncio.Queue | None:
    global _router_queue, _router_worker_started
    if not SOULOS_ROUTER_LOG_PATH:
        return None
    if _router_queue is None:
        _router_queue = asyncio.Queue(maxsize=256)
    if not _router_worker_started:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_router_log_worker(_router_queue))
            _router_worker_started = True
        except RuntimeError:
            return None
    return _router_queue


def log_router_decision_async(
    features: DualProcessFeatures,
    *,
    run_system_2: bool,
    threshold: float,
    bot_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Non-blocking enqueue; drops if queue full."""
    queue = _ensure_router_worker()
    if queue is None:
        return
    record = {
        "ts": time.time(),
        "bot_id": bot_id,
        "run_system_2": run_system_2,
        "threshold": threshold,
        "features": asdict(features),
        **(extra or {}),
    }
    try:
        queue.put_nowait(record)
    except asyncio.QueueFull:
        logger.debug("Router log queue full; dropping decision record")


def decide_reflect(
    current_msv: dict[str, Any],
    runtime_config: dict[str, Any] | None,
    *,
    query: str = "",
    retrieval_weak: bool = False,
    best_distance: float | None = None,
    contract_incomplete: bool = False,
    reflect_force: bool = False,
    bot_id: str | None = None,
) -> tuple[bool, DualProcessFeatures]:
    features = features_from_msv(
        current_msv,
        query=query,
        retrieval_weak=retrieval_weak,
        best_distance=best_distance,
        contract_incomplete=contract_incomplete,
    )
    threshold = system1_threshold(runtime_config)
    run = should_run_system_2(
        features,
        threshold=threshold,
        uncertainty_trigger_value=uncertainty_trigger(runtime_config),
        reflect_force=reflect_force,
    )
    log_router_decision_async(
        features, run_system_2=run, threshold=threshold, bot_id=bot_id
    )
    return run, features
