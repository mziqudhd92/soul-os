"""FastAPI reference app: hybrid sidecar with mock LLM."""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from soulos.hybrid import SoulHybridClient

app = FastAPI(title="SoulOS FastAPI Hybrid Example", version="0.3.2")

KERNEL_URL = os.getenv("SOULOS_KERNEL_URL", "http://localhost:8001").rstrip("/")
EXTERNAL_KEY = os.getenv("SOULOS_EXTERNAL_KEY", "fastapi-hybrid-demo")
SOUL_PATH = os.getenv("SOULOS_SOUL_PATH", "examples/support-bot/support-bot.soul.json")

soul_client = SoulHybridClient(base_url=KERNEL_URL)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


async def mock_llm(system_prompt: str, _ctx: dict) -> str:
    """Replace with Bedrock/OpenAI/LiteLLM in production."""
    return f"[mock] Answering with persona context ({len(system_prompt)} chars)."


@app.get("/healthz")
async def healthz():
    local_ok = True
    kernel_ok = False
    kernel_detail: dict | str = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{KERNEL_URL}/ready")
            kernel_detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            kernel_ok = resp.status_code == 200
    except httpx.HTTPError as e:
        kernel_detail = str(e)
    status = "ok" if local_ok and kernel_ok else "degraded"
    code = 200 if status == "ok" else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=code,
        content={
            "status": status,
            "local": "ok",
            "kernel": "ok" if kernel_ok else "error",
            "kernel_url": KERNEL_URL,
            "kernel_detail": kernel_detail,
        },
    )


@app.on_event("startup")
async def bootstrap():
    if os.path.isfile(SOUL_PATH):
        await soul_client.ensure_avatar(EXTERNAL_KEY, SOUL_PATH)


@app.post("/chat")
async def chat(payload: ChatRequest):
    result = await soul_client.run_turn(
        payload.message,
        mock_llm,
        external_key=EXTERNAL_KEY,
        soul=SOUL_PATH if os.path.isfile(SOUL_PATH) else None,
        session_id=payload.session_id,
    )
    return {"reply": result["reply"], "system_prompt_len": len(result["system_prompt"])}


@app.on_event("shutdown")
async def shutdown():
    await soul_client.close()
