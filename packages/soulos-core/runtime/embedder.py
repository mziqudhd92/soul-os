"""PERCEIVE: text embeddings via inference API."""

import httpx

from config import EMBED_MODEL_NAME, EMBEDDING_DIMENSION, INFERENCE_API_URL
from runtime.errors import INFERENCE_DOWN, MEMORY_DIM_MISMATCH, SoulOSProblem


class Embedder:
    async def get_embedding(self, text_content: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{INFERENCE_API_URL}/api/embeddings",
                json={"model": EMBED_MODEL_NAME, "prompt": text_content},
                timeout=30.0,
            )
            if resp.status_code != 200:
                raise SoulOSProblem(
                    INFERENCE_DOWN,
                    503,
                    f"Failed to generate embedding: {resp.text}",
                )
            embedding = resp.json()["embedding"]
            if len(embedding) != EMBEDDING_DIMENSION:
                raise SoulOSProblem(
                    MEMORY_DIM_MISMATCH,
                    422,
                    f"Embedding dimension {len(embedding)} != configured {EMBEDDING_DIMENSION}",
                    extra={"expected": EMBEDDING_DIMENSION, "actual": len(embedding)},
                )
            return embedding
