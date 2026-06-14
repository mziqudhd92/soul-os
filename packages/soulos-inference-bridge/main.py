"""Ollama-compatible inference bridge for SoulOS."""

import json
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backends.registry import get_backend

app = FastAPI(title="SoulOS Inference Bridge")
_backend = None


def backend():
    global _backend
    if _backend is None:
        _backend = get_backend()
    return _backend


@app.get("/")
async def health():
    return {"status": "ok", "service": "soulos-inference-bridge", "mode": os.getenv("BRIDGE_MODE", "mock")}


@app.post("/api/pull")
async def api_pull(_: Request):
    return {"status": "success"}


@app.post("/api/embeddings")
async def api_embeddings(payload: dict[str, Any]):
    text = payload.get("prompt", "")
    model = payload.get("model", "")
    embedding = await backend().embed(text, model)
    return {"embedding": embedding}


@app.post("/api/generate")
async def api_generate(payload: dict[str, Any]):
    prompt = payload.get("prompt", "")
    model = payload.get("model", "")
    stream = payload.get("stream", True)
    format_json = payload.get("format") == "json"

    if not stream:
        text = await backend().generate(prompt, model, format_json=format_json)
        return {"response": text, "done": True}

    async def stream_lines():
        async for chunk in backend().generate_stream(prompt, model):
            if chunk:
                line = json.dumps({"response": chunk, "done": False})
                yield line + "\n"
        yield json.dumps({"response": "", "done": True}) + "\n"

    return StreamingResponse(stream_lines(), media_type="application/x-ndjson")


@app.exception_handler(Exception)
async def unhandled(exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})
