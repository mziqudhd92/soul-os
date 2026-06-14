"""Deterministic mock backend for CI and offline dev."""

import hashlib
import json
import os
from collections.abc import AsyncIterator

from backends.base import InferenceBackend


class MockBackend(InferenceBackend):
    def __init__(self) -> None:
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))

    async def embed(self, text: str, model: str) -> list[float]:
        digest = hashlib.sha256(f"{model}:{text}".encode()).digest()
        values = []
        for i in range(self.dimension):
            values.append((digest[i % len(digest)] / 255.0) * 0.1)
        return values

    async def generate_stream(self, prompt: str, model: str) -> AsyncIterator[str]:
        reply = f"[mock:{model}] Echo: {prompt[-120:]}"
        for word in reply.split():
            yield word + " "

    async def generate(self, prompt: str, model: str, format_json: bool = False) -> str:
        if format_json:
            return json.dumps(
                {
                    "hexaco": {
                        "H": 0.8,
                        "E": 0.5,
                        "X": 0.6,
                        "A": 0.9,
                        "C": 0.5,
                        "O": 0.7,
                    },
                    "moral_foundations": {
                        "care_harm": 0.8,
                        "fairness_cheating": 0.8,
                        "loyalty_betrayal": 0.7,
                        "authority_subversion": 0.5,
                        "sanctity_degradation": 0.4,
                    },
                    "drives": {
                        "curiosity": 0.6,
                        "autonomy": 0.5,
                        "social_approval": 0.6,
                    },
                    "epistemic_uncertainty": 0.2,
                    "inner_monologue": "Mock reflector processed the message.",
                }
            )
        return f"[mock:{model}] {prompt[-200:]}"
