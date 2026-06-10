"""PERCEIVE: text embeddings via inference API."""

import httpx
from fastapi import HTTPException

from config import EMBED_MODEL_NAME, INFERENCE_API_URL


class Embedder:
    async def get_embedding(self, text_content: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{INFERENCE_API_URL}/api/embeddings",
                json={"model": EMBED_MODEL_NAME, "prompt": text_content},
                timeout=30.0,
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate embedding: {resp.text}",
                )
            return resp.json()["embedding"]
