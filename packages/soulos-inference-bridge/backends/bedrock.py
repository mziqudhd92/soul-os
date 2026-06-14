"""AWS Bedrock backend via boto3."""

import json
import os
from collections.abc import AsyncIterator

import boto3

from backends.base import InferenceBackend


class BedrockBackend(InferenceBackend):
    def __init__(self) -> None:
        region = os.getenv("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.chat_model = os.getenv(
            "BEDROCK_CHAT_MODEL_ID", "amazon.nova-lite-v1:0"
        )
        self.embed_model = os.getenv(
            "BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"
        )

    async def embed(self, text: str, model: str) -> list[float]:
        model_id = model or self.embed_model
        body = json.dumps({"inputText": text})
        resp = self.client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(resp["body"].read())
        if "embedding" in payload:
            return payload["embedding"]
        if "embeddings" in payload:
            return payload["embeddings"][0]["embedding"]
        raise RuntimeError(f"Unexpected Bedrock embed response: {payload}")

    async def generate_stream(self, prompt: str, model: str) -> AsyncIterator[str]:
        model_id = model or self.chat_model
        response = self.client.converse_stream(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )
        stream = response.get("stream")
        if not stream:
            yield ""
            return
        for event in stream:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]
                if "text" in delta:
                    yield delta["text"]

    async def generate(self, prompt: str, model: str, format_json: bool = False) -> str:
        model_id = model or self.chat_model
        response = self.client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )
        output = response.get("output", {})
        message = output.get("message", {})
        parts = message.get("content", [])
        texts = [p.get("text", "") for p in parts if "text" in p]
        return "".join(texts)
