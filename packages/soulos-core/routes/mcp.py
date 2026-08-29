"""MCP HTTP/SSE transport endpoints."""

from fastapi import APIRouter, Request
from mcp.server.sse import SseServerTransport

from mcp_server import mcp_server

router = APIRouter(tags=["mcp"])
sse_transport = SseServerTransport("/mcp/messages")


@router.get("/mcp/sse")
async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


@router.post("/mcp/messages")
async def handle_messages(request: Request):
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )
