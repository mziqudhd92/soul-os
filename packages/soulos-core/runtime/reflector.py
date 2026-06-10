"""REFLECT: System 2 metacognitive MSV update."""

import json
import logging

import httpx
from sqlalchemy import text

from config import INFERENCE_API_URL, MODEL_NAME, engine

logger = logging.getLogger(__name__)


async def run_system_2_reflector(
    bot_id: str, message: str, current_msv: dict
) -> dict:
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
            if resp.status_code == 200:
                new_msv = json.loads(resp.json()["response"])
                async with engine.begin() as conn:
                    await conn.execute(
                        text("UPDATE bots SET current_msv = :msv WHERE id = :id"),
                        {"msv": json.dumps(new_msv), "id": bot_id},
                    )
                return new_msv
        except Exception as e:
            logger.error("System 2 Reflection failed: %s", e)

    return current_msv
