"""REFLECT: System 2 metacognitive MSV update."""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import text

from runtime.boot_memory import sync_memory_on_boot
from runtime.crystallization import apply_crystallization_if_needed
from config import INFERENCE_API_URL, MODEL_NAME, engine

logger = logging.getLogger(__name__)


@dataclass
class ReflectorResult:
    msv: dict[str, Any]
    latency_ms: int
    reasoning_tokens: int
    loop_count: int = 1
    active_mcp_tools: list[str] | None = None


async def run_system_2_reflector(
    bot_id: str,
    message: str,
    current_msv: dict,
    active_mcp_tools: list[str] | None = None,
) -> ReflectorResult:
    prompt = f"""
    System: You are the subconscious metacognitive layer of an AI agent.
    Analyze the user's message: "{message}"
    Current State: {json.dumps(current_msv)}

    Task: Output a strict JSON object updating the MSV.
    1. Adjust HEXACO traits (-1.0 to 1.0) based on emotional impact.
    2. Assess 'epistemic_uncertainty' (0.0 to 1.0).
    3. Generate a 1-sentence 'inner_monologue' detailing how the message aligns or conflicts with the agent's Moral Foundations and Drives.
    Format strictly as JSON: {{"hexaco": {{"H": float, "E": float, "X": float, "A": float, "C": float, "O": float}}, "moral_foundations": {{"care_harm": float, "fairness_cheating": float, "loyalty_betrayal": float, "authority_subversion": float, "sanctity_degradation": float}}, "drives": {{"curiosity": float, "autonomy": float, "social_approval": float}}, "epistemic_uncertainty": float, "inner_monologue": "string"}}
    """

    started = time.monotonic()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{INFERENCE_API_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
                timeout=30.0,
            )
            latency_ms = int((time.monotonic() - started) * 1000)
            if resp.status_code == 200:
                response_text = resp.json()["response"]
                new_msv = json.loads(response_text)
                async with engine.begin() as conn:
                    await conn.execute(
                        text("UPDATE bots SET current_msv = :msv WHERE id = :id"),
                        {"msv": json.dumps(new_msv), "id": bot_id},
                    )
                    baseline_row = await conn.execute(
                        text("SELECT baseline_msv FROM bots WHERE id = :id"),
                        {"id": bot_id},
                    )
                    baseline_fetch = baseline_row.fetchone()
                    baseline = baseline_fetch.baseline_msv if baseline_fetch else current_msv
                    if isinstance(baseline, str):
                        baseline = json.loads(baseline)
                    await apply_crystallization_if_needed(
                        conn, bot_id, baseline or current_msv, new_msv
                    )
                tools = list(active_mcp_tools or [])
                if "run_system_2_reflector" not in tools:
                    tools.append("system_2_reflector")
                return ReflectorResult(
                    msv=new_msv,
                    latency_ms=latency_ms,
                    reasoning_tokens=max(1, len(prompt) // 4),
                    loop_count=1,
                    active_mcp_tools=tools,
                )
        except Exception as e:
            logger.error("System 2 Reflection failed: %s", e)

    return ReflectorResult(
        msv=current_msv,
        latency_ms=int((time.monotonic() - started) * 1000),
        reasoning_tokens=0,
        loop_count=1,
        active_mcp_tools=list(active_mcp_tools or []),
    )
