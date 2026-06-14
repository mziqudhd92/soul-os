"""GCP Vertex AI backend."""

import json
import os
from collections.abc import AsyncIterator

from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel

import vertexai

from backends.base import InferenceBackend


class VertexBackend(InferenceBackend):
    def __init__(self) -> None:
        project = os.getenv("VERTEX_PROJECT_ID", "")
        location = os.getenv("VERTEX_LOCATION", "us-central1")
        if not project:
            raise ValueError("VERTEX_PROJECT_ID is required for BRIDGE_MODE=vertex")
        aiplatform.init(project=project, location=location)
        vertexai.init(project=project, location=location)
        self.chat_model = os.getenv("VERTEX_CHAT_MODEL", "gemini-2.0-flash-001")
        self.embed_model = os.getenv(
            "VERTEX_EMBED_MODEL", "text-embedding-004"
        )

    async def embed(self, text: str, model: str) -> list[float]:
        model_name = model or self.embed_model
        embedding_model = TextEmbeddingModel.from_pretrained(model_name)
        embeddings = embedding_model.get_embeddings([text])
        return list(embeddings[0].values)

    async def generate_stream(self, prompt: str, model: str) -> AsyncIterator[str]:
        model_name = model or self.chat_model
        generative = GenerativeModel(model_name)
        response = generative.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def generate(self, prompt: str, model: str, format_json: bool = False) -> str:
        model_name = model or self.chat_model
        generative = GenerativeModel(model_name)
        response = generative.generate_content(prompt)
        return response.text or ""
