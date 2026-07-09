"""Tenant isolation: scope avatar operations to owner_id."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext
from runtime.errors import ACCESS_DENIED, BOT_NOT_FOUND, SoulOSProblem


async def verify_bot_access(
    db: AsyncConnection, bot_id: str, account: AccountContext
) -> None:
    if account.account_id is None:
        return

    result = await db.execute(
        text("SELECT owner_id FROM bots WHERE id = :id"),
        {"id": bot_id},
    )
    row = result.fetchone()
    if not row:
        raise SoulOSProblem(BOT_NOT_FOUND, 404, f"Bot not found: {bot_id}")
    if row.owner_id is None or str(row.owner_id) != account.account_id:
        raise SoulOSProblem(ACCESS_DENIED, 403, "Access denied for this bot")
