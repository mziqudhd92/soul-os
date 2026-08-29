"""MCP HTTP/SSE transport endpoints."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["mcp"])

_sse_transport = None


def _get_sse_transport():
    global _sse_transport
    if _sse_transport is None:
        from mcp.server.sse import SseServerTransport

        _sse_transport = SseServerTransport("/mcp/messages")
    return _sse_transport


@router.get("/mcp/sse")
async def handle_sse(request: Request):
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
    sse_transport = _get_sse_transport()
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )
