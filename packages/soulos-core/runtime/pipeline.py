"""Orchestrator: dual-process ACT (System 1) + REFLECT (System 2) multiplexed SSE."""

import asyncio
import json
import logging
import time

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import INFERENCE_API_URL, MODEL_NAME
from soul_validation import default_msv_dict
from runtime.cognitive_telemetry import (
    confidence_from_msv,
    format_cognitive_state_sse,
    format_sse,
    merge_runtime_config,
    system1_threshold,
)
from runtime.reflector import run_system_2_reflector

logger = logging.getLogger(__name__)


class ChatPipeline:
    async def load_current_msv(self, db: AsyncConnection, bot_id: str) -> dict:
        result = await db.execute(
            text("SELECT current_msv FROM bots WHERE id = :id"), {"id": bot_id}
        )
        bot_record = result.fetchone()
        default_msv = default_msv_dict()

        if bot_record and bot_record.current_msv:
            if isinstance(bot_record.current_msv, str):
                return json.loads(bot_record.current_msv)
            return bot_record.current_msv
        return default_msv

    async def load_runtime_config(self, db: AsyncConnection, bot_id: str) -> dict:
        result = await db.execute(
            text("SELECT runtime_config FROM bots WHERE id = :id"), {"id": bot_id}
        )
        row = result.fetchone()
        if row and row.runtime_config:
            if isinstance(row.runtime_config, str):
                return merge_runtime_config(json.loads(row.runtime_config))
            return merge_runtime_config(row.runtime_config)
        return merge_runtime_config(None)

    async def generate_chat_stream(
        self,
        bot_id: str,
        message: str,
        context: list[str],
        db: AsyncConnection,
    ):
        current_msv = await self.load_current_msv(db, bot_id)
        runtime_config = await self.load_runtime_config(db, bot_id)
        threshold = system1_threshold(runtime_config)
        confidence = confidence_from_msv(current_msv)

        yield format_cognitive_state_sse(
            "system_1_heuristic",
            system_1={
                "confidence_score": round(confidence, 3),
                "cached_response_triggered": False,
                "latency_ms": 0,
            },
        )

        if confidence < threshold:
            yield format_cognitive_state_sse(
                "system_2_deliberation",
                system_1={
                    "confidence_score": round(confidence, 3),
                    "cached_response_triggered": False,
                    "latency_ms": 0,
                },
                system_2={
                    "loop_count": 0,
                    "reasoning_tokens": 0,
                    "active_mcp_tools": [],
                    "latency_ms": 0,
                },
            )

        reflector_task = asyncio.create_task(
            run_system_2_reflector(bot_id, message, current_msv)
        )
        reflector_yielded = False
        system1_started = time.monotonic()
        first_token_ms: int | None = None

        context_str = "\n".join(context)
        prompt = (
            f"System: You are an AI. Internal State: {json.dumps(current_msv)}\n"
            f"Context:\n{context_str}\n\nUser: {message}\nAssistant:"
        )

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{INFERENCE_API_URL}/api/generate",
                json={"model": MODEL_NAME, "prompt": prompt},
                timeout=60.0,
            ) as response:
                if response.status_code != 200:
                    yield format_sse("error", {"message": "Failed to generate"})
                    return

                async for chunk in response.aiter_lines():
                    if not chunk:
                        continue
                    try:
                        data = json.loads(chunk)
                        if "response" in data:
                            if first_token_ms is None:
                                first_token_ms = int(
                                    (time.monotonic() - system1_started) * 1000
                                )
                                yield format_cognitive_state_sse(
                                    "system_1_heuristic",
                                    system_1={
                                        "confidence_score": round(confidence, 3),
                                        "cached_response_triggered": False,
                                        "latency_ms": first_token_ms,
                                    },
                                )
                            yield format_sse(
                                "message", {"text": data["response"]}
                            )

                        if reflector_task.done() and not reflector_yielded:
                            reflector_result = reflector_task.result()
                            new_msv = reflector_result.msv
                            yield format_sse("msv_update", new_msv)
                            yield format_cognitive_state_sse(
                                "system_2_deliberation",
                                system_2={
                                    "loop_count": reflector_result.loop_count,
                                    "reasoning_tokens": reflector_result.reasoning_tokens,
                                    "active_mcp_tools": reflector_result.active_mcp_tools
                                    or [],
                                    "latency_ms": reflector_result.latency_ms,
                                },
                            )
                            reflector_yielded = True
                    except json.JSONDecodeError:
                        pass

        if not reflector_yielded:
            reflector_result = await reflector_task
            yield format_sse("msv_update", reflector_result.msv)
            yield format_cognitive_state_sse(
                "system_2_deliberation",
                system_2={
                    "loop_count": reflector_result.loop_count,
                    "reasoning_tokens": reflector_result.reasoning_tokens,
                    "active_mcp_tools": reflector_result.active_mcp_tools or [],
                    "latency_ms": reflector_result.latency_ms,
                },
            )
