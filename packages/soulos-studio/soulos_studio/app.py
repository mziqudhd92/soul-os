"""FastAPI app for SoulOS Studio."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from soulos_studio.docs_reader import (
    build_docs_catalog,
    get_doc_content,
    get_tutorial_content,
    get_tutorials_catalog,
)
from soulos_studio.soul_form import (
    ATTACHMENT_STYLES,
    DRIVE_META,
    HEXACO_LABELS,
    MORAL_META,
    build_soul_payload,
    default_form,
    parse_soul_file,
    validate_soul,
)
from soulos_studio.soul_markdown import build_soul_markdown, parse_soul_markdown

STATIC_DIR = Path(__file__).resolve().parent / "static"
KERNEL_URL = os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000").rstrip("/")

app = FastAPI(title="SoulOS Studio", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class FormPayload(BaseModel):
    name: str
    role: str
    description: str
    attachment_style: str
    hexaco: dict[str, float]
    moral_foundations: dict[str, float]
    drives: dict[str, float]
    epistemic_uncertainty: float
    inner_monologue: str


class SoulPayload(BaseModel):
    soul: dict


class TextPayload(BaseModel):
    text: str


class ChatPayload(BaseModel):
    avatar_id: str
    message: str


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/meta")
async def meta():
    return {
        "hexaco_labels": HEXACO_LABELS,
        "moral_meta": [{"key": k, "label": l} for k, l in MORAL_META],
        "drive_meta": [{"key": k, "label": l} for k, l in DRIVE_META],
        "attachment_styles": list(ATTACHMENT_STYLES),
        "kernel_url": KERNEL_URL,
    }


@app.get("/api/defaults")
async def get_defaults():
    return default_form()


@app.post("/api/build")
async def build_soul(form: FormPayload):
    payload = build_soul_payload(form.model_dump())
    try:
        validate_soul(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return payload


@app.post("/api/build-soul")
async def build_soul_text(form: FormPayload):
    text = build_soul_markdown(form.model_dump())
    return {"text": text}


@app.post("/api/import-text")
async def import_soul_text(body: TextPayload):
    try:
        form = parse_soul_markdown(body.text)
        payload = build_soul_payload(form)
        validate_soul(payload)
        return {"form": form, "soul": payload}
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/validate")
async def validate_endpoint(body: SoulPayload):
    try:
        validate_soul(body.soul)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"ok": True}


@app.post("/api/import")
async def import_soul(body: SoulPayload):
    try:
        form = parse_soul_file(body.soul)
        payload = build_soul_payload(form)
        validate_soul(payload)
        return {"form": form, "soul": payload}
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/register")
async def register_avatar(body: SoulPayload):
    try:
        validate_soul(body.soul)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{KERNEL_URL}/v1/avatars",
                json=body.soul,
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Kernel unreachable at {KERNEL_URL}. Start soulos-kernel or set SOULOS_KERNEL_URL.",
        ) from e

    data = res.json()
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=data.get("detail", "register failed"))
    return data


@app.get("/api/docs/catalog")
async def docs_catalog():
    return build_docs_catalog()


@app.get("/api/docs/content")
async def docs_content(path: str):
    try:
        return get_doc_content(path)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/kernel-health")
async def kernel_health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{KERNEL_URL}/health")
        if res.status_code == 200:
            return {"ok": True, "url": KERNEL_URL, "service": res.json().get("service")}
        return {"ok": False, "url": KERNEL_URL, "detail": f"status {res.status_code}"}
    except httpx.RequestError as e:
        return {"ok": False, "url": KERNEL_URL, "detail": str(e)}


@app.get("/api/tutorials")
async def tutorials_list():
    return {"tutorials": get_tutorials_catalog()}


@app.get("/api/tutorials/{tutorial_id}")
async def tutorial_content(tutorial_id: str):
    try:
        return get_tutorial_content(tutorial_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/chat")
async def chat_stream(body: ChatPayload):
    async def stream():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{KERNEL_URL}/chat/generate",
                    json={"bot_id": body.avatar_id, "message": body.message},
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except httpx.RequestError:
            yield b"event: error\ndata: Kernel unreachable\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
