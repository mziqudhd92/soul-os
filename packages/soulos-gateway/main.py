"""SoulOS Cloud gateway — validates API keys and proxies to soulos-kernel."""

import logging

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from config import (
    ACCOUNT_ID_HEADER,
    GATEWAY_SECRET,
    GATEWAY_SECRET_HEADER,
    KERNEL_URL,
)
from keys import lookup_api_key
from rate_limit import rate_limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SoulOS Cloud Gateway")

HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def _forward_headers(request: Request, account_id: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in request.headers.items():
        lower = name.lower()
        if lower in HOP_HEADERS or lower == "authorization":
            continue
        headers[name] = value
    headers[ACCOUNT_ID_HEADER] = account_id
    headers[GATEWAY_SECRET_HEADER] = GATEWAY_SECRET
    return headers


def _outbound_headers(response: httpx.Response) -> dict[str, str]:
    return {
        k: v
        for k, v in response.headers.items()
        if k.lower() not in HOP_HEADERS
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "soulos-gateway"}


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy(full_path: str, request: Request):
    token = _extract_bearer_token(request.headers.get("authorization"))
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer API key")

    record = lookup_api_key(token)
    if not record:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not rate_limiter.allow(token, record):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    upstream_path = f"/{full_path}" if full_path else "/"
    url = f"{KERNEL_URL}{upstream_path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = _forward_headers(request, record.account_id)
    body = await request.body()
    is_sse = upstream_path.endswith("/chat/generate") or upstream_path.startswith("/mcp/")

    timeout = httpx.Timeout(600.0, connect=30.0)

    try:
        if is_sse:
            client = httpx.AsyncClient(timeout=timeout)
            upstream_req = client.build_request(
                request.method,
                url,
                headers=headers,
                content=body if request.method != "GET" else None,
            )
            upstream_res = await client.send(upstream_req, stream=True)

            if upstream_res.status_code >= 400:
                error_body = await upstream_res.aread()
                await upstream_res.aclose()
                await client.aclose()
                return Response(
                    content=error_body,
                    status_code=upstream_res.status_code,
                    headers=_outbound_headers(upstream_res),
                    media_type=upstream_res.headers.get("content-type"),
                )

            async def stream_body():
                try:
                    async for chunk in upstream_res.aiter_bytes():
                        yield chunk
                finally:
                    await upstream_res.aclose()
                    await client.aclose()

            return StreamingResponse(
                stream_body(),
                status_code=upstream_res.status_code,
                headers=_outbound_headers(upstream_res),
                media_type=upstream_res.headers.get("content-type"),
            )

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                request.method,
                url,
                headers=headers,
                content=body if request.method != "GET" else None,
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=_outbound_headers(response),
                media_type=response.headers.get("content-type"),
            )
    except httpx.RequestError as e:
        logger.error("Upstream kernel error: %s", e)
        raise HTTPException(status_code=502, detail="Kernel unavailable") from e
