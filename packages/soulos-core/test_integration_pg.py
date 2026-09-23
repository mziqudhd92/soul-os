"""Live Postgres integration: migrations are idempotent and create core tables."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration


def _skip_unless_integration() -> None:
    if os.getenv("SOULOS_INTEGRATION", "").strip() not in ("1", "true", "yes"):
        pytest.skip("Set SOULOS_INTEGRATION=1 to run Postgres integration tests")


@pytest.mark.asyncio
async def test_init_database_idempotent_creates_tables() -> None:
    _skip_unless_integration()
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:changeme_local_dev@localhost:5432/soulos",
    )

    from runtime.bootstrap import init_database
    from runtime.migrations import MIGRATIONS_TABLE

    first = await init_database(database_url)
    second = await init_database(database_url)
    assert isinstance(first, list)
    assert second == []

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            migrations = await conn.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM information_schema.tables "
                    f"WHERE table_name = '{MIGRATIONS_TABLE}'"
                    ")"
                )
            )
            bots = await conn.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'bots'"
                    ")"
                )
            )
            assert migrations.scalar() is True
            assert bots.scalar() is True
    finally:
        await engine.dispose()
