"""Orchestrator: dual-process ACT (System 1) + REFLECT (System 2) multiplexed SSE."""

import asyncio
import json
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import INFERENCE_API_URL, MODEL_NAME
from soul_validation import default_msv_dict
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

    async def generate_chat_stream(
        self,
        bot_id: str,
        message: str,
        context: list[str],
        db: AsyncConnection,
    ):
        current_msv = await self.load_current_msv(db, bot_id)

        reflector_task = asyncio.create_task(
            run_system_2_reflector(bot_id, message, current_msv)
        )
        reflector_yielded = False

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
                    yield "event: error\ndata: Failed to generate\n\n"
                    return

                async for chunk in response.aiter_lines():
                    if not chunk:
                        continue
                    try:
                        data = json.loads(chunk)
                        if "response" in data:
                            yield (
                                f"event: message\ndata: "
                                f"{json.dumps({'text': data['response']})}\n\n"
                            )

                        if reflector_task.done() and not reflector_yielded:
                            new_msv = reflector_task.result()
                            yield f"event: msv_update\ndata: {json.dumps(new_msv)}\n\n"
                            reflector_yielded = True
                    except json.JSONDecodeError:
                        pass

        if not reflector_yielded:
            new_msv = await reflector_task
            yield f"event: msv_update\ndata: {json.dumps(new_msv)}\n\n"
