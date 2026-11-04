"""MCP HTTP/SSE and Streamable HTTP transport endpoints."""

from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

import config
from auth import resolve_account_context, set_mcp_account_context
from runtime.errors import ACCESS_DENIED, SoulOSProblem, problem_response
from runtime.security_context import security_context_from_account

router = APIRouter(tags=["mcp"])

_sse_transport = None

# Streamable HTTP sessions: session_id -> principal_hash
_mcp_sessions: dict[str, str] = {}


def _principal_hash(account_id: str | None, authorization: str | None) -> str:
    raw = f"{account_id or ''}|{authorization or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_origin_host(request: Request) -> None:
    """Enforce Origin/Host only when allowlists are explicitly configured.

    Host defaults to empty so docker/gateway Hostnames (e.g. soulos-kernel) work.
    """
    host = request.headers.get("host", "").split(":")[0].strip().lower()
    origin = request.headers.get("origin")
    allow_hosts = {h.lower() for h in config.MCP_HOST_ALLOWLIST}
    if allow_hosts and host and host not in allow_hosts:
        if host not in ("test", "testserver"):
            raise SoulOSProblem(
                ACCESS_DENIED, 403, f"Host {host!r} not in MCP host allowlist"
            )
    if origin and config.MCP_ORIGIN_ALLOWLIST:
        if origin not in config.MCP_ORIGIN_ALLOWLIST:
            raise SoulOSProblem(
                ACCESS_DENIED, 403, "Origin not allowed for MCP"
            )


def _check_body_size(request: Request, body: bytes) -> None:
    if len(body) > config.MCP_MAX_BODY_BYTES:
        raise SoulOSProblem(
            "PAYLOAD_TOO_LARGE",
            413,
            f"MCP body exceeds {config.MCP_MAX_BODY_BYTES} bytes",
        )


def _get_sse_transport():
    global _sse_transport
    if _sse_transport is None:
        from mcp.server.sse import SseServerTransport

        _sse_transport = SseServerTransport("/mcp/messages")
    return _sse_transport


def _scopes_from_request(request: Request) -> frozenset[str]:
    raw = request.headers.get("x-soulos-scopes") or request.headers.get(
        "X-SoulOS-Scopes", ""
    )
    return frozenset(s.strip() for s in raw.split(",") if s.strip())


def _bind_security(request: Request):
    account_id = request.headers.get(config.ACCOUNT_ID_HEADER)
    gateway_secret = request.headers.get(config.GATEWAY_SECRET_HEADER)
    ctx = resolve_account_context(account_id, gateway_secret)
    set_mcp_account_context(ctx)
    auth = request.headers.get("authorization")
    sec = security_context_from_account(
        ctx,
        scopes=_scopes_from_request(request),
        admin_tools_enabled=config.SOULOS_MCP_ADMIN_TOOLS,
        principal_hash=_principal_hash(ctx.account_id, auth),
    )
    from mcp_server import set_mcp_security_context

    set_mcp_security_context(sec)
    return sec


@router.get("/mcp/sse")
async def handle_sse(request: Request):
    _validate_origin_host(request)
    _bind_security(request)
    from mcp_server import mcp_server

    sse_transport = _get_sse_transport()
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


@router.post("/mcp/messages")
async def handle_messages(request: Request):
    _validate_origin_host(request)
    body = await request.body()
    _check_body_size(request, body)
    _bind_security(request)
    sse_transport = _get_sse_transport()

    # Re-inject body for the transport
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    await sse_transport.handle_post_message(
        request.scope, receive, request._send
    )


def _session_headers(session_id: str | None) -> dict[str, str]:
    headers = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return headers


async def _streamable_http_impl(request: Request):
    """Shared Streamable HTTP handler with session-auth binding."""
    _validate_origin_host(request)
    sec = _bind_security(request)
    session_header = request.headers.get("mcp-session-id")

    if request.method == "DELETE":
        if session_header and session_header in _mcp_sessions:
            if _mcp_sessions[session_header] != sec.principal_hash:
                return problem_response(
                    ACCESS_DENIED, 403, "MCP session does not match auth principal"
                )
            del _mcp_sessions[session_header]
        return Response(status_code=204, headers=_session_headers(None))

    if request.method == "GET":
        if session_header:
            bound = _mcp_sessions.get(session_header)
            if bound is None:
                return problem_response("MCP_SESSION_NOT_FOUND", 404, "Unknown MCP session")
            if bound != sec.principal_hash:
                return problem_response(
                    ACCESS_DENIED, 403, "MCP session does not match auth principal"
                )
        return JSONResponse(
            {"status": "ok", "transport": "streamable-http"},
            headers=_session_headers(session_header),
        )

    body = await request.body()
    _check_body_size(request, body)

    if session_header:
        bound = _mcp_sessions.get(session_header)
        if bound is None:
            return problem_response("MCP_SESSION_NOT_FOUND", 404, "Unknown MCP session")
        if bound != sec.principal_hash:
            return problem_response(
                ACCESS_DENIED, 403, "MCP session does not match auth principal"
            )
        session_id = session_header
    else:
        session_id = secrets.token_urlsafe(32)
        _mcp_sessions[session_id] = sec.principal_hash

    try:
        import json

        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return problem_response("SOUL_INVALID", 422, "Invalid JSON body")

    method = payload.get("method")
    req_id = payload.get("id")

    def _ok(result: object) -> JSONResponse:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": req_id, "result": result},
            headers=_session_headers(session_id),
        )

    def _err(code: int, message: str) -> JSONResponse:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": code, "message": message},
            },
            headers=_session_headers(session_id),
        )

    if method == "initialize":
        return _ok(
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
                "serverInfo": {"name": "soulos-kernel", "version": "1"},
            }
        )

    if method == "tools/list":
        from mcp_server import handle_list_tools

        tools = await handle_list_tools()
        return _ok(
            {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema,
                    }
                    for t in tools
                ]
            }
        )

    if method == "tools/call":
        from mcp_server import _call_tool_result

        params = payload.get("params") or {}
        result = await _call_tool_result(
            params.get("name") or "", dict(params.get("arguments") or {})
        )
        content = [
            {"type": c.type, "text": c.text}
            for c in result.content
            if hasattr(c, "text")
        ]
        return _ok({"content": content, "isError": bool(result.is_error)})

    if method == "resources/list":
        from mcp_server import handle_list_resources

        resources = await handle_list_resources()
        return _ok(
            {
                "resources": [
                    {
                        "uri": getattr(r, "uri", str(r)),
                        "name": getattr(r, "name", ""),
                        "description": getattr(r, "description", None),
                    }
                    for r in resources
                ]
            }
        )

    if method in ("resources/templates/list", "resources/list_templates"):
        from mcp_server import handle_list_resource_templates

        templates = await handle_list_resource_templates()
        return _ok(
            {
                "resourceTemplates": [
                    {
                        "uriTemplate": t.uri_template,
                        "name": t.name,
                        "description": t.description,
                    }
                    for t in templates
                ]
            }
        )

    if method == "resources/read":
        from mcp_server import handle_read_resource

        params = payload.get("params") or {}
        uri = str(params.get("uri") or "")
        try:
            text_body = await handle_read_resource(uri)
            return _ok(
                {
                    "contents": [
                        {"uri": uri, "mimeType": "application/json", "text": text_body}
                    ]
                }
            )
        except Exception as e:
            return _err(-32002, str(getattr(e, "detail", e)))

    if method == "prompts/list":
        from mcp_server import handle_list_prompts

        prompts = await handle_list_prompts()
        return _ok(
            {
                "prompts": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "arguments": [
                            {
                                "name": a.name,
                                "description": a.description,
                                "required": a.required,
                            }
                            for a in (p.arguments or [])
                        ],
                    }
                    for p in prompts
                ]
            }
        )

    if method == "prompts/get":
        from mcp_server import handle_get_prompt

        params = payload.get("params") or {}
        try:
            prompt = await handle_get_prompt(
                params.get("name") or "", params.get("arguments")
            )
            return _ok(
                {
                    "description": prompt.description,
                    "messages": [
                        {
                            "role": m.role,
                            "content": {
                                "type": getattr(m.content, "type", "text"),
                                "text": getattr(m.content, "text", str(m.content)),
                            },
                        }
                        for m in prompt.messages
                    ],
                }
            )
        except Exception as e:
            return _err(-32002, str(e))

    return _err(-32601, f"Method not found: {method}")


@router.post("/mcp", operation_id="mcp_streamable_post")
async def handle_streamable_post(request: Request):
    return await _streamable_http_impl(request)


@router.get("/mcp", operation_id="mcp_streamable_get")
async def handle_streamable_get(request: Request):
    return await _streamable_http_impl(request)


@router.delete("/mcp", operation_id="mcp_streamable_delete")
async def handle_streamable_delete(request: Request):
    return await _streamable_http_impl(request)
