"""Backend factory."""

import os

from backends.base import InferenceBackend
from backends.bedrock import BedrockBackend
from backends.mock import MockBackend


def get_backend() -> InferenceBackend:
    mode = os.getenv("BRIDGE_MODE", "mock").lower()
    if mode == "mock":
        return MockBackend()
    if mode == "bedrock":
        return BedrockBackend()
    if mode == "vertex":
        from backends.vertex import VertexBackend

        return VertexBackend()
    raise ValueError(f"Unknown BRIDGE_MODE: {mode}")
