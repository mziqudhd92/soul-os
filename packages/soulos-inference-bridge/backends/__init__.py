"""Inference backend implementations for the Ollama-compatible bridge."""

from backends.base import InferenceBackend
from backends.registry import get_backend

__all__ = ["InferenceBackend", "get_backend"]
