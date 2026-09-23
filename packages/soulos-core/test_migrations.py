import pytest

from runtime.migrations import (
    MIGRATIONS,
    MIGRATIONS_TABLE,
    Migration,
    SchemaTooNewError,
    apply_migrations,
    migration_status,
    validate_migrations,
)


class FakeResult:
    def __init__(self, rows=(), scalar=None):
        self._rows = list(rows)
        self._scalar = scalar

    def fetchall(self):
        return self._rows

    def scalar(self):
        return self._scalar


class FakeConn:
    def __init__(self, applied=(), table_exists=True):
        self.applied = set(applied)
        self.table_exists = table_exists
        self.statements: list[str] = []

    async def execute(self, query, params=None):
        q = str(query)
        self.statements.append(q)
        if q.startswith(f"SELECT version FROM {MIGRATIONS_TABLE}"):
            return FakeResult(rows=[(v,) for v in sorted(self.applied)])
        if "to_regclass" in q:
            return FakeResult(scalar=MIGRATIONS_TABLE if self.table_exists else None)
        if q.startswith(f"INSERT INTO {MIGRATIONS_TABLE}"):
            self.applied.add(params["v"])
        return FakeResult()


def _toy(n: int) -> list[Migration]:
    return [Migration(i, f"m{i}", lambda i=i: [f"-- stmt {i}"]) for i in range(1, n + 1)]


def test_registry_versions_are_contiguous():
    validate_migrations(MIGRATIONS)
    assert MIGRATIONS[0].name.startswith("baseline")


def test_validate_rejects_gaps_and_duplicates():
    with pytest.raises(ValueError):
        validate_migrations([Migration(1, "a", list), Migration(3, "c", list)])
    with pytest.raises(ValueError):
        validate_migrations([Migration(1, "a", list), Migration(1, "b", list)])


def test_baseline_is_idempotent_for_pre_migration_databases():
    for stmt in MIGRATIONS[0].statements():
        s = " ".join(stmt.split()).upper()
        assert "IF NOT EXISTS" in s, stmt


@pytest.mark.asyncio
async def test_apply_fresh_database_runs_all_in_order_under_lock():
    conn = FakeConn()
    applied = await apply_migrations(conn, _toy(3))
    assert applied == [1, 2, 3]
    assert "pg_advisory_xact_lock" in conn.statements[0]
    body = [s for s in conn.statements if s.startswith("-- stmt")]
    assert body == ["-- stmt 1", "-- stmt 2", "-- stmt 3"]


@pytest.mark.asyncio
async def test_apply_only_pending():
    conn = FakeConn(applied={1, 2})
    assert await apply_migrations(conn, _toy(3)) == [3]
    assert "-- stmt 1" not in conn.statements


@pytest.mark.asyncio
async def test_apply_twice_is_noop():
    conn = FakeConn()
    await apply_migrations(conn, _toy(2))
    assert await apply_migrations(conn, _toy(2)) == []


@pytest.mark.asyncio
async def test_refuses_schema_newer_than_kernel():
    conn = FakeConn(applied={1, 2, 3, 4})
    with pytest.raises(SchemaTooNewError):
        await apply_migrations(conn, _toy(3))


@pytest.mark.asyncio
async def test_status_before_table_exists_reports_all_pending():
    conn = FakeConn(table_exists=False)
    rows = await migration_status(conn, _toy(2))
    assert [r["applied"] for r in rows] == [False, False]


@pytest.mark.asyncio
async def test_status_marks_applied():
    conn = FakeConn(applied={1})
    rows = await migration_status(conn, _toy(2))
    assert [(r["version"], r["applied"]) for r in rows] == [(1, True), (2, False)]
