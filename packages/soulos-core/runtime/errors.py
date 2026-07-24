"""RFC 7807 Problem Details for SoulOS kernel errors."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_CONTENT_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE = "https://soulos.dev/problems/"

# Stable machine-readable codes (extension field `code`)
INFERENCE_DOWN = "INFERENCE_DOWN"
SOUL_INVALID = "SOUL_INVALID"
MEMORY_DIM_MISMATCH = "MEMORY_DIM_MISMATCH"
BOT_NOT_FOUND = "BOT_NOT_FOUND"
ACCESS_DENIED = "ACCESS_DENIED"
READY_DEGRADED = "READY_DEGRADED"
VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"

_CODE_TITLES: dict[str, str] = {
    INFERENCE_DOWN: "Inference service unavailable",
    SOUL_INVALID: "Invalid soul payload",
    MEMORY_DIM_MISMATCH: "Embedding dimension mismatch",
    BOT_NOT_FOUND: "Bot not found",
    ACCESS_DENIED: "Access denied",
    READY_DEGRADED: "Kernel not ready",
    VALIDATION_ERROR: "Request validation failed",
    INTERNAL_ERROR: "Internal server error",
}


class SoulOSProblem(Exception):
    """Raise for RFC 7807 problem responses."""

    def __init__(
        self,
        code: str,
        status: int,
        detail: str,
        *,
        type_suffix: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status = status
        self.detail = detail
        self.type_suffix = type_suffix or code.lower().replace("_", "-")
        self.extra = extra or {}
        super().__init__(detail)

    @property
    def status_code(self) -> int:
        return self.status


def problem_body(
    code: str,
    status: int,
    detail: str,
    *,
    type_suffix: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = _CODE_TITLES.get(code, code.replace("_", " ").title())
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}{type_suffix or code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
    }
    if extra:
        body.update(extra)
    return body


def problem_response(
    code: str,
    status: int,
    detail: str,
    *,
    type_suffix: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=problem_body(code, status, detail, type_suffix=type_suffix, extra=extra),
        media_type=PROBLEM_CONTENT_TYPE,
    )


def _map_http_detail_to_code(status: int, detail: str) -> str:
    lowered = detail.lower()
    if status == 404 and "bot" in lowered:
        return BOT_NOT_FOUND
    if status == 403 and "access" in lowered:
        return ACCESS_DENIED
    if status == 422:
        return SOUL_INVALID if "soul" in lowered else VALIDATION_ERROR
    if status == 500 and "embedding" in lowered:
        return INFERENCE_DOWN
    if status == 401:
        return ACCESS_DENIED
    return INTERNAL_ERROR


async def soulos_problem_handler(_request: Request, exc: SoulOSProblem) -> JSONResponse:
    return problem_response(
        exc.code,
        exc.status,
        exc.detail,
        type_suffix=exc.type_suffix,
        extra=exc.extra or None,
    )


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    code = _map_http_detail_to_code(exc.status_code, detail)
    return problem_response(code, exc.status_code, detail)


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    detail = "; ".join(
        f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg', '')}"
        for err in exc.errors()
    )
    return problem_response(VALIDATION_ERROR, 422, detail or "Validation failed")


def register_exception_handlers(app) -> None:
    app.add_exception_handler(SoulOSProblem, soulos_problem_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
