"""Tenant isolation: scope avatar operations to owner_id."""

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext


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
        raise HTTPException(status_code=404, detail="Bot not found")
    if row.owner_id is None or str(row.owner_id) != account.account_id:
        raise HTTPException(status_code=403, detail="Access denied")
