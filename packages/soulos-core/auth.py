"""Account context from SoulOS Cloud gateway (trusted internal headers)."""

import secrets
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Header, HTTPException

import config
from config import ACCOUNT_ID_HEADER, GATEWAY_SECRET, GATEWAY_SECRET_HEADER

_mcp_account_context: ContextVar["AccountContext | None"] = ContextVar(
    "mcp_account_context", default=None
)


@dataclass(frozen=True)
class AccountContext:
    """Tenant scope for multi-tenant Cloud deployments."""

    account_id: str | None


def set_mcp_account_context(ctx: AccountContext) -> None:
    _mcp_account_context.set(ctx)


def get_mcp_account_context() -> AccountContext:
    ctx = _mcp_account_context.get()
    if ctx is None:
        return AccountContext(account_id=None)
    return ctx


def resolve_account_context(
    account_id: str | None,
    gateway_secret: str | None,
) -> AccountContext:
    trusted = bool(
        account_id
        and gateway_secret
        and secrets.compare_digest(gateway_secret, GATEWAY_SECRET)
    )

    if config.REQUIRE_AUTH:
        if not trusted:
            raise HTTPException(
                status_code=401,
                detail="Cloud mode requires gateway authentication",
            )
        return AccountContext(account_id=account_id)

    if trusted:
        return AccountContext(account_id=account_id)
    return AccountContext(account_id=None)


async def get_account_context(
    x_soulos_account_id: str | None = Header(None, alias=ACCOUNT_ID_HEADER),
    x_soulos_gateway_secret: str | None = Header(None, alias=GATEWAY_SECRET_HEADER),
) -> AccountContext:
    return resolve_account_context(x_soulos_account_id, x_soulos_gateway_secret)
