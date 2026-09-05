"""Health and readiness probes."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from dependencies import get_db
from runtime.errors import READY_DEGRADED, problem_response
from runtime.readiness import build_ready_payload
from versioning import get_product_version

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "soulos-kernel",
        "version": get_product_version(),
    }


@router.get("/ready")
async def ready_check(db: AsyncConnection = Depends(get_db)):
    payload = await build_ready_payload(db)
    if payload["status"] == "ok":
        return JSONResponse(status_code=200, content=payload)
    checks = payload.get("checks", {})
    detail = (
        f"Kernel degraded: database={checks.get('database')}, "
        f"inference={checks.get('inference')}"
    )
    return problem_response(
        READY_DEGRADED,
        503,
        detail,
        extra={k: v for k, v in payload.items() if k not in ("status",)},
    )
