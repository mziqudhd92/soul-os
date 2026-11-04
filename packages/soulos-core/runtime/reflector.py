"""REFLECT: System 2 metacognitive MSV update with constrained merges."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import text

from config import (
    INFERENCE_API_URL,
    INFERENCE_MODE,
    MODEL_NAME,
    engine,
    inference_headers,
)
from runtime.crystallization import apply_crystallization_if_needed
from runtime.mcp_client import MAX_TOOL_ITERATIONS
from runtime.mcp_outbound import run_budgeted_outbound_calls
from runtime.msv_update import merge_reflected_msv

logger = logging.getLogger(__name__)


@dataclass
class ReflectorResult:
    msv: dict[str, Any]
    latency_ms: int
    reasoning_tokens: int
    loop_count: int = 1
    active_mcp_tools: list[str] | None = None


def _msv_prompt(message: str, current_msv: dict, tools: list[str], *, final: bool) -> str:
    tool_block = ""
    if tools and not final:
        tool_block = (
            "\nOptional outbound tools (namespaced): "
            + ", ".join(tools)
            + "\nTo call a tool before updating MSV, return JSON: "
            '{"tool_call": {"name": "<namespaced>", "arguments": {}}}. '
            "Otherwise return the MSV update JSON only.\n"
        )
    elif final:
        tool_block = (
            "\nTool budget exhausted or tools unavailable. "
            "Do NOT return tool_call. Return the MSV update JSON only.\n"
        )
    return f"""
    System: You are the subconscious metacognitive layer of an AI agent.
    Analyze the user's message: "{message}"
    Current State: {json.dumps(current_msv)}
    {tool_block}
    Task: Output a strict JSON object updating the MSV.
    1. Adjust HEXACO traits (-1.0 to 1.0) based on emotional impact.
    2. Assess 'epistemic_uncertainty' (0.0 to 1.0).
    3. Generate a 1-sentence 'inner_monologue' detailing how the message aligns or conflicts with the agent's Moral Foundations and Drives.
    Format strictly as JSON: {{"hexaco": {{"H": float, "E": float, "X": float, "A": float, "C": float, "O": float}}, "moral_foundations": {{"care_harm": float, "fairness_cheating": float, "loyalty_betrayal": float, "authority_subversion": float, "sanctity_degradation": float}}, "drives": {{"curiosity": float, "autonomy": float, "social_approval": float}}, "epistemic_uncertainty": float, "inner_monologue": "string"}}
    """


async def _generate_json(prompt: str) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{INFERENCE_API_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
            headers=inference_headers(),
            timeout=30.0,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        if resp.status_code != 200:
            raise RuntimeError(f"inference status {resp.status_code}")
        response_text = resp.json()["response"]
        proposed = json.loads(response_text)
        if not isinstance(proposed, dict):
            raise ValueError("reflector returned non-object JSON")
        return proposed, latency_ms


async def run_system_2_reflector(
    bot_id: str,
    message: str,
    current_msv: dict,
    active_mcp_tools: list[str] | None = None,
    *,
    retrieval_weak: bool = False,
) -> ReflectorResult:
    started = time.monotonic()
    tools = list(active_mcp_tools or [])
    loop_count = 1
    working_message = message

    if INFERENCE_MODE == "embeddings_only":
        new_msv = dict(current_msv)
        snippet = message.replace("\n", " ")[:120]
        new_msv["inner_monologue"] = (
            f"Embeddings-only mode: noted user message without LLM reflect ({snippet})."
        )
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE bots SET current_msv = :msv WHERE id = :id"),
                {"msv": json.dumps(new_msv), "id": bot_id},
            )
        if "system_2_reflector" not in tools:
            tools.append("system_2_reflector")
        return ReflectorResult(
            msv=new_msv,
            latency_ms=int((time.monotonic() - started) * 1000),
            reasoning_tokens=0,
            loop_count=1,
            active_mcp_tools=tools,
        )

    try:
        proposed: dict[str, Any] | None = None
        latency_ms = 0
        prompt_tokens = 0
        for iteration in range(max(1, MAX_TOOL_ITERATIONS + 1)):
            final = iteration >= MAX_TOOL_ITERATIONS or not tools
            prompt = _msv_prompt(
                working_message, current_msv, tools, final=final
            )
            prompt_tokens += max(1, len(prompt) // 4)
            proposed, latency_ms = await _generate_json(prompt)
            loop_count = iteration + 1
            tool_call = proposed.get("tool_call") if isinstance(proposed, dict) else None
            if (
                not final
                and isinstance(tool_call, dict)
                and tool_call.get("name") in tools
            ):
                results = await run_budgeted_outbound_calls([tool_call])
                working_message = (
                    f"{working_message}\n\nOutbound tool results:\n"
                    + "\n".join(results)
                )
                continue
            break

        if not isinstance(proposed, dict) or "hexaco" not in proposed:
            # If last response was only a tool_call, force one final MSV pass.
            prompt = _msv_prompt(working_message, current_msv, tools, final=True)
            proposed, latency_ms = await _generate_json(prompt)
            loop_count += 1

        new_msv = merge_reflected_msv(
            current_msv,
            proposed,
            retrieval_weak=retrieval_weak,
        )
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
        if "system_2_reflector" not in tools:
            tools.append("system_2_reflector")
        return ReflectorResult(
            msv=new_msv,
            latency_ms=latency_ms,
            reasoning_tokens=prompt_tokens,
            loop_count=loop_count,
            active_mcp_tools=tools,
        )
    except Exception as e:
        logger.error("System 2 Reflection failed: %s", e)

    return ReflectorResult(
        msv=current_msv,
        latency_ms=int((time.monotonic() - started) * 1000),
        reasoning_tokens=0,
        loop_count=loop_count,
        active_mcp_tools=list(active_mcp_tools or []),
    )
