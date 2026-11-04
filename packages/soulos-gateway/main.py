"""SoulOS Cloud gateway — validates API keys and proxies to soulos-kernel."""

import json
import logging
import time
import uuid

import httpx
from config import (
    ACCOUNT_ID_HEADER,
    GATEWAY_SECRET,
    GATEWAY_SECRET_HEADER,
    KERNEL_URL,
    SCOPES_HEADER,
)
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from keys import ApiKeyRecord, hash_api_key, lookup_api_key
from rate_limit import rate_limiter
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
access_logger = logging.getLogger("soulos.gateway.access")

REQUEST_ID_HEADER = "X-Request-Id"

app = FastAPI(title="SoulOS Cloud Gateway")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = None
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            access_logger.info(
                "%s",
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "account_id": request.headers.get(ACCOUNT_ID_HEADER),
                    },
                    separators=(",", ":"),
                ),
            )


app.add_middleware(RequestIdMiddleware)

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

# Concurrent MCP SSE / Streamable HTTP streams per API key hash.
_MCP_MAX_STREAMS = 10
_mcp_stream_counts: dict[str, int] = {}


def _mcp_stream_acquire(key_hash: str) -> bool:
    n = _mcp_stream_counts.get(key_hash, 0)
    if n >= _MCP_MAX_STREAMS:
        return False
    _mcp_stream_counts[key_hash] = n + 1
    return True


def _mcp_stream_release(key_hash: str) -> None:
    n = _mcp_stream_counts.get(key_hash, 0)
    if n <= 1:
        _mcp_stream_counts.pop(key_hash, None)
    else:
        _mcp_stream_counts[key_hash] = n - 1


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


# Never trust clients to set these — gateway injects from the API key record.
_PRIVILEGED_HEADERS = frozenset(
    {
        "authorization",
        ACCOUNT_ID_HEADER.lower(),
        GATEWAY_SECRET_HEADER.lower(),
        SCOPES_HEADER.lower(),
    }
)


def _forward_headers(request: Request, record: ApiKeyRecord) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in request.headers.items():
        lower = name.lower()
        if lower in HOP_HEADERS or lower in _PRIVILEGED_HEADERS:
            continue
        headers[name] = value
    headers[ACCOUNT_ID_HEADER] = record.account_id
    headers[GATEWAY_SECRET_HEADER] = GATEWAY_SECRET
    # Always overwrite scopes from the key store (empty = no admin scopes).
    if record.scopes:
        headers[SCOPES_HEADER] = ",".join(record.scopes)
    return headers


def _outbound_headers(response: httpx.Response) -> dict[str, str]:
    headers: dict[str, str] = {}
    session_id = None
    for k, v in response.headers.items():
        lower = k.lower()
        if lower in HOP_HEADERS:
            continue
        if lower == "mcp-session-id":
            session_id = v
            continue
        headers[k] = v
    # Preserve MCP session binding end-to-end (single canonical header).
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    headers["X-Accel-Buffering"] = "no"
    return headers


def _is_mcp_stream_path(upstream_path: str) -> bool:
    return (
        upstream_path == "/mcp"
        or upstream_path.startswith("/mcp/")
        or upstream_path.endswith("/chat/generate")
    )


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

    if not rate_limiter.allow(hash_api_key(token), record):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    upstream_path = f"/{full_path}" if full_path else "/"
    url = f"{KERNEL_URL}{upstream_path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = _forward_headers(request, record)
    body = await request.body()
    is_sse = _is_mcp_stream_path(upstream_path)
    key_hash = hash_api_key(token)
    holding_mcp_slot = False
    if is_sse and upstream_path.startswith("/mcp"):
        if not _mcp_stream_acquire(key_hash):
            raise HTTPException(
                status_code=429, detail="Too many concurrent MCP streams for this API key"
            )
        holding_mcp_slot = True

    timeout = httpx.Timeout(600.0, connect=30.0)

    try:
        if is_sse:
            client = httpx.AsyncClient(timeout=timeout)
            upstream_req = client.build_request(
                request.method,
                url,
                headers=headers,
                content=body if request.method not in ("GET", "DELETE") else None,
            )
            upstream_res = await client.send(upstream_req, stream=True)

            if upstream_res.status_code >= 400:
                error_body = await upstream_res.aread()
                await upstream_res.aclose()
                await client.aclose()
                if holding_mcp_slot:
                    _mcp_stream_release(key_hash)
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
                    if holding_mcp_slot:
                        _mcp_stream_release(key_hash)

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
        if holding_mcp_slot:
            _mcp_stream_release(key_hash)
        logger.error("Upstream kernel error: %s", e)
        raise HTTPException(status_code=502, detail="Kernel unavailable") from e
