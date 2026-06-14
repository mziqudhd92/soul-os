import pytest
from httpx import AsyncClient, ASGITransport
from dependencies import get_db, get_embedder, get_llm_service
from main import app

VALID_SOUL = {
    "name": "Test Avatar",
    "role": "Tester",
    "description": "A test avatar for validation.",
    "attachment_style": "Secure",
    "baseline_msv": {
        "hexaco": {"H": 0.9, "E": 0.5, "X": 0.6, "A": 0.8, "C": 0.7, "O": 0.6},
        "moral_foundations": {
            "care_harm": 0.9,
            "fairness_cheating": 0.8,
            "loyalty_betrayal": 0.7,
            "authority_subversion": 0.5,
            "sanctity_degradation": 0.4,
        },
        "drives": {"curiosity": 0.6, "autonomy": 0.4, "social_approval": 0.7},
        "epistemic_uncertainty": 0.1,
        "inner_monologue": "Ready for testing.",
    },
}


class MockConnection:
    def __init__(self):
        self.last_insert = None

    async def execute(self, query, params=None):
        class MockResult:
            def __init__(self, row_id="123e4567-e89b-12d3-a456-426614174000"):
                self.row_id = row_id

            def fetchone(self):
                row = type("Row", (), {})()
                row.id = self.row_id
                row.content = "Mocked retrieved memory"
                return row

            def fetchall(self):
                row = type("Row", (), {})()
                row.content = "Mocked retrieved memory"
                return [row]

        if params and "INSERT INTO bots" in str(query):
            MockConnection.last_insert = params
            return MockResult()
        return MockResult()

    async def commit(self):
        pass


async def mock_get_db():
    yield MockConnection()


from config import EMBEDDING_DIMENSION


class MockEmbedder:
    async def get_embedding(self, text: str) -> list[float]:
        return [0.1] * EMBEDDING_DIMENSION


class MockLLMService:
    async def generate_chat_stream(self, bot_id: str, message: str, context: list[str], db):
        yield "event: msv_update\ndata: {\"hexaco\": {\"H\": 0.8, \"E\": 0.5, \"X\": 0.6, \"A\": 0.9, \"C\": 0.5, \"O\": 0.7}}\n\n"
        yield "event: message\ndata: {\"text\": \"Mock response\"}\n\n"


app.dependency_overrides[get_db] = mock_get_db
app.dependency_overrides[get_embedder] = MockEmbedder
app.dependency_overrides[get_llm_service] = lambda: MockLLMService()


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "soulos-kernel"}


@pytest.mark.asyncio
async def test_register_avatar_valid_soul():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/avatars", json=VALID_SOUL)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Avatar"
    assert "id" in data
    assert data["baseline_msv"]["hexaco"]["H"] == 0.9
    assert data["current_msv"]["hexaco"]["H"] == 0.9


@pytest.mark.asyncio
async def test_register_avatar_invalid_hexaco():
    invalid = {
        **VALID_SOUL,
        "baseline_msv": {
            **VALID_SOUL["baseline_msv"],
            "hexaco": {"H": 2.0, "E": 0.5, "X": 0.6, "A": 0.8, "C": 0.7, "O": 0.6},
        },
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/avatars", json=invalid)

    assert response.status_code == 422
    assert "Soul validation failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_memory():
    payload = {
        "bot_id": "123e4567-e89b-12d3-a456-426614174000",
        "content": "I remember the time we refactored this code to use TDD.",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/memory/ingest", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "success"}


@pytest.mark.asyncio
async def test_retrieve_memory():
    payload = {
        "bot_id": "123e4567-e89b-12d3-a456-426614174000",
        "query": "What do you remember about refactoring?",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/memory/retrieve", json=payload)

    assert response.status_code == 200
    assert "memories" in response.json()
    assert response.json()["memories"] == ["Mocked retrieved memory"]


@pytest.mark.asyncio
async def test_update_state_valid_msv():
    payload = {
        "bot_id": "123e4567-e89b-12d3-a456-426614174000",
        "new_msv": VALID_SOUL["baseline_msv"],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/state/update", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_update_state_invalid_msv():
    payload = {
        "bot_id": "123e4567-e89b-12d3-a456-426614174000",
        "new_msv": {
            "hexaco": {"H": 9.0, "E": 0.5, "X": 0.6, "A": 0.8, "C": 0.7, "O": 0.6},
            "moral_foundations": VALID_SOUL["baseline_msv"]["moral_foundations"],
            "drives": VALID_SOUL["baseline_msv"]["drives"],
            "epistemic_uncertainty": 0.1,
            "inner_monologue": "Bad state.",
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/state/update", json=payload)

    assert response.status_code == 422
    assert "MSV validation failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_generate():
    payload = {
        "bot_id": "123e4567-e89b-12d3-a456-426614174000",
        "message": "Hello Nexus Prime, what can you do?",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/chat/generate", json=payload)

    assert response.status_code == 200
    assert "Mock response" in response.text
