import pytest
from fastapi import HTTPException

from auth import AccountContext
from tenant import verify_bot_access


class MockRow:
    def __init__(self, owner_id):
        self.owner_id = owner_id


class MockResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class MockConnection:
    def __init__(self, owner_id):
        self.owner_id = owner_id

    async def execute(self, query, params=None):
        return MockResult(MockRow(self.owner_id))


@pytest.mark.asyncio
async def test_verify_bot_access_open_mode_skips_check():
    db = MockConnection(owner_id="other-account")
    await verify_bot_access(db, "bot-1", AccountContext(account_id=None))


@pytest.mark.asyncio
async def test_verify_bot_access_allows_owner():
    owner = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    db = MockConnection(owner_id=owner)
    await verify_bot_access(db, "bot-1", AccountContext(account_id=owner))


@pytest.mark.asyncio
async def test_verify_bot_access_denies_other_account():
    db = MockConnection(owner_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    with pytest.raises(HTTPException) as exc:
        await verify_bot_access(
            db, "bot-1", AccountContext(account_id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_bot_access_not_found():
    class EmptyConnection:
        async def execute(self, query, params=None):
            return MockResult(None)

    with pytest.raises(HTTPException) as exc:
        await verify_bot_access(
            EmptyConnection(), "missing-bot", AccountContext(account_id="acct-1")
        )
    assert exc.value.status_code == 404
