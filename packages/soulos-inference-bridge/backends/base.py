"""Abstract inference backend."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class InferenceBackend(ABC):
    @abstractmethod
    async def embed(self, text: str, model: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(self, prompt: str, model: str) -> AsyncIterator[str]:
        """Yield Ollama-style response token chunks."""
        raise NotImplementedError

    @abstractmethod
    async def generate(self, prompt: str, model: str, format_json: bool = False) -> str:
        raise NotImplementedError
