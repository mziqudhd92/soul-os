"""Avatar registration, ensure, and SoulPack import."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from dependencies import get_db
from runtime.avatars import ensure_avatar_record, register_avatar_record
from runtime.errors import (
    SOUL_INVALID,
    SOULPACK_INVALID,
    SOULPACK_LICENSE_REJECTED,
    SOULPACK_NOT_FOUND,
    SoulOSProblem,
)
from runtime.soulpacks import (
    SoulPackError,
    SoulPackLicenseError,
    SoulPackNotFoundError,
    compile_pack,
    default_external_key,
    list_packs,
)
from schemas import EnsureAvatarRequest, ImportSoulPackRequest
from soul_compile import parse_soul_request_bundle

router = APIRouter(tags=["avatars"])


@router.post("/v1/avatars")
async def register_avatar(
    request: Request,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    raw = await request.body()
    content_type = request.headers.get("content-type", "")
    filename_hint = request.headers.get("x-filename")
    try:
        payload, runtime_config = parse_soul_request_bundle(
            raw, content_type, filename_hint
        )
        return await register_avatar_record(
            db, account.account_id, payload, runtime_config
        )
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e


@router.post("/v1/avatars/ensure")
async def ensure_avatar(
    payload: EnsureAvatarRequest,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    try:
        return await ensure_avatar_record(
            db,
            account.account_id,
            payload.external_key,
            payload.soul,
            payload.runtime_config,
        )
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e


@router.get("/v1/soulpacks")
async def get_soulpacks(q: str | None = None):
    packs = list_packs(q=q)
    return {"packs": packs, "total": len(packs)}


@router.post("/v1/avatars/import-soulpack")
async def import_soulpack_avatar(
    payload: ImportSoulPackRequest,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    try:
        soul, runtime_config, warnings = compile_pack(
            payload.pack_id.strip(),
            msv_preset=payload.msv_preset,
        )
    except SoulPackNotFoundError as e:
        raise SoulOSProblem(SOULPACK_NOT_FOUND, 404, str(e)) from e
    except SoulPackLicenseError as e:
        raise SoulOSProblem(SOULPACK_LICENSE_REJECTED, 422, str(e)) from e
    except SoulPackError as e:
        raise SoulOSProblem(SOULPACK_INVALID, 422, str(e)) from e

    merged_runtime = dict(runtime_config)
    if payload.runtime_config:
        merged_runtime.update(payload.runtime_config)

    version = merged_runtime.get("source", {}).get("version") or "0.0.0"
    pack_id = merged_runtime.get("source", {}).get("id") or payload.pack_id.strip()
    external_key = payload.external_key or default_external_key(pack_id, str(version))

    if not payload.persist:
        return {
            "soul": soul,
            "runtime_config": merged_runtime,
            "warnings": warnings,
            "external_key": external_key,
        }

    try:
        record = await ensure_avatar_record(
            db,
            account.account_id,
            external_key,
            soul,
            merged_runtime,
        )
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e

    return {
        **record,
        "warnings": warnings,
        "external_key": external_key,
        "runtime_config": merged_runtime,
    }
