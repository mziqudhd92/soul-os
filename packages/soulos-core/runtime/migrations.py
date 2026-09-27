"""Versioned schema migrations for the kernel database.

Each migration is applied once, in order, and recorded in ``soulos_schema_migrations``.
Append new migrations to ``MIGRATIONS`` — never edit or reorder applied ones.

FTS / GIN indexes that need ``CREATE INDEX CONCURRENTLY`` are listed on
``Migration.concurrent_indexes`` and applied **after** the transactional
migration commits (see ``apply_concurrent_indexes``).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from config import DATABASE_URL, EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)

MIGRATIONS_TABLE = "soulos_schema_migrations"
CONCURRENT_INDEX_TABLE = "soulos_concurrent_indexes"
# Arbitrary constant key for pg_advisory_xact_lock; serializes concurrent kernel boots.
ADVISORY_LOCK_KEY = 0x50_55_4C_05


class SchemaTooNewError(RuntimeError):
    """Database was migrated by a newer kernel than the one booting."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: Callable[[], list[str]]
    concurrent_indexes: tuple[str, ...] = field(default_factory=tuple)


def _baseline() -> list[str]:
    # Idempotent so databases created before versioned migrations (<= 0.3.2) adopt cleanly.
    return [
        "CREATE EXTENSION IF NOT EXISTS vector;",
        """
        CREATE TABLE IF NOT EXISTS bots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_id UUID,
            name TEXT NOT NULL,
            baseline_msv JSONB,
            current_msv JSONB,
            role VARCHAR(255),
            description TEXT,
            attachment_style VARCHAR(50),
            capabilities JSONB,
            hourly_rate INTEGER,
            status VARCHAR(50),
            avatar_url VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS episodic_memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            embedding vector({EMBEDDING_DIMENSION})
        );
        """,
        "ALTER TABLE bots ADD COLUMN IF NOT EXISTS attachment_style VARCHAR(50);",
        "ALTER TABLE bots ADD COLUMN IF NOT EXISTS runtime_config JSONB;",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64);",
        "ALTER TABLE bots ADD COLUMN IF NOT EXISTS cognitive_meta JSONB;",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS session_id VARCHAR(128);",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS created_at "
        "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE bots ADD COLUMN IF NOT EXISTS external_key VARCHAR(128);",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_bots_owner_external_key "
        "ON bots (owner_id, external_key) WHERE external_key IS NOT NULL;",
        """
        CREATE TABLE IF NOT EXISTS turn_sessions (
            bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
            session_id VARCHAR(128) NOT NULL,
            current_step TEXT NOT NULL,
            slots JSONB NOT NULL DEFAULT '{}'::jsonb,
            turn_version INTEGER NOT NULL DEFAULT 0,
            last_idempotency_key VARCHAR(128),
            last_success_response JSONB,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (bot_id, session_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_turn_sessions_updated_at "
        "ON turn_sessions (updated_at);",
    ]


def _memory_lookup_indexes() -> list[str]:
    return [
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_bot_session "
        "ON episodic_memories (bot_id, session_id);",
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_bot_source_hash "
        "ON episodic_memories (bot_id, source_hash) WHERE source_hash IS NOT NULL;",
    ]


def _phase_b_ml_schema() -> list[str]:
    """Importance, semantic provenance, conversation shared memory, handoff idempotency."""
    return [
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS importance REAL DEFAULT 0.5;",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS memory_kind VARCHAR(32) "
        "DEFAULT 'episodic';",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS supersedes UUID;",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS source_memory_ids JSONB;",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS time_range_start "
        "TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE episodic_memories ADD COLUMN IF NOT EXISTS time_range_end "
        "TIMESTAMP WITH TIME ZONE;",
        f"""
        CREATE TABLE IF NOT EXISTS conversation_memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            conversation_id VARCHAR(128) NOT NULL,
            content TEXT NOT NULL,
            embedding vector({EMBEDDING_DIMENSION}),
            source_bot_id UUID REFERENCES bots(id) ON DELETE SET NULL,
            importance REAL DEFAULT 0.5,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_conversation_memories_tenant_conv "
        "ON conversation_memories (tenant_id, conversation_id);",
        """
        CREATE TABLE IF NOT EXISTS handoff_idempotency (
            tenant_id UUID,
            idempotency_key VARCHAR(128) NOT NULL,
            response JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (tenant_id, idempotency_key)
        );
        """,
        # Partial unique for null tenant (local auth-off)
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_handoff_idempotency_null_tenant "
        "ON handoff_idempotency (idempotency_key) WHERE tenant_id IS NULL;",
    ]


_FTS_EPISODIC = (
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_episodic_memories_content_fts "
    "ON episodic_memories USING GIN (to_tsvector('english', content))"
)
_FTS_CONVERSATION = (
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversation_memories_content_fts "
    "ON conversation_memories USING GIN (to_tsvector('english', content))"
)


MIGRATIONS: list[Migration] = [
    Migration(1, "baseline_0_3_2", _baseline),
    Migration(2, "episodic_memory_lookup_indexes", _memory_lookup_indexes),
    Migration(
        3,
        "phase_b_ml_memory",
        _phase_b_ml_schema,
        concurrent_indexes=(_FTS_EPISODIC, _FTS_CONVERSATION),
    ),
]


def validate_migrations(migrations: list[Migration]) -> None:
    versions = [m.version for m in migrations]
    if versions != list(range(1, len(migrations) + 1)):
        raise ValueError(f"Migration versions must be contiguous from 1: {versions}")


async def applied_versions(conn: AsyncConnection) -> set[int]:
    result = await conn.execute(text(f"SELECT version FROM {MIGRATIONS_TABLE}"))
    return {row[0] for row in result.fetchall()}


async def apply_migrations(
    conn: AsyncConnection, migrations: list[Migration] | None = None
) -> list[int]:
    """Apply pending migrations inside the caller's transaction; return versions applied."""
    migrations = MIGRATIONS if migrations is None else migrations
    validate_migrations(migrations)

    await conn.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY}
    )
    await conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    done = await applied_versions(conn)
    latest = migrations[-1].version if migrations else 0
    if done and max(done) > latest:
        raise SchemaTooNewError(
            f"Database schema is at version {max(done)} but this kernel only knows "
            f"up to {latest}. Upgrade SoulOS before connecting to this database."
        )

    applied: list[int] = []
    for migration in migrations:
        if migration.version in done:
            continue
        logger.info("Applying migration %03d_%s", migration.version, migration.name)
        for statement in migration.statements():
            await conn.execute(text(statement))
        await conn.execute(
            text(f"INSERT INTO {MIGRATIONS_TABLE} (version, name) VALUES (:v, :n)"),
            {"v": migration.version, "n": migration.name},
        )
        applied.append(migration.version)
    return applied


async def apply_concurrent_indexes(
    database_url: str = DATABASE_URL,
    migrations: list[Migration] | None = None,
) -> list[str]:
    """Create CONCURRENTLY indexes outside a transaction; idempotent via tracking table."""
    migrations = MIGRATIONS if migrations is None else migrations
    engine = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    created: list[str] = []
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {CONCURRENT_INDEX_TABLE} (
                        index_name TEXT PRIMARY KEY,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            )
            done_rows = await conn.execute(
                text(f"SELECT index_name FROM {CONCURRENT_INDEX_TABLE}")
            )
            done = {row[0] for row in done_rows.fetchall()}
            for migration in migrations:
                for stmt in migration.concurrent_indexes:
                    # Derive a stable name from the statement
                    name = "idx_unknown"
                    if "IF NOT EXISTS" in stmt:
                        parts = stmt.split("IF NOT EXISTS", 1)[1].strip().split()
                        if parts:
                            name = parts[0]
                    if name in done:
                        continue
                    logger.info("Applying concurrent index %s", name)
                    try:
                        await conn.execute(text(stmt))
                        await conn.execute(
                            text(
                                f"INSERT INTO {CONCURRENT_INDEX_TABLE} (index_name) "
                                f"VALUES (:n) ON CONFLICT DO NOTHING"
                            ),
                            {"n": name},
                        )
                        created.append(name)
                    except Exception as e:
                        logger.warning(
                            "Concurrent index %s failed (may already exist): %s", name, e
                        )
    finally:
        await engine.dispose()
    return created


async def migration_status(
    conn: AsyncConnection, migrations: list[Migration] | None = None
) -> list[dict]:
    migrations = MIGRATIONS if migrations is None else migrations
    exists = await conn.execute(
        text("SELECT to_regclass(:t)"), {"t": MIGRATIONS_TABLE}
    )
    done = await applied_versions(conn) if exists.scalar() else set()
    return [
        {"version": m.version, "name": m.name, "applied": m.version in done}
        for m in migrations
    ]
