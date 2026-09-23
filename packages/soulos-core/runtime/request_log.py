"""HTTP request correlation and structured access logs."""

from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import ACCOUNT_ID_HEADER

REQUEST_ID_HEADER = "X-Request-Id"
logger = logging.getLogger("soulos.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign or propagate X-Request-Id and emit one JSON access log line."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response: Response | None = None
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if response is not None:
                response.headers[REQUEST_ID_HEADER] = request_id
            account_id = request.headers.get(ACCOUNT_ID_HEADER)
            logger.info(
                "%s",
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "latency_ms": latency_ms,
                        "account_id": account_id,
                    },
                    separators=(",", ":"),
                ),
            )
