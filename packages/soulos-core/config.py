"""SoulOS kernel configuration from environment."""

import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:changeme_local_dev@db:5432/senticore",
)
INFERENCE_API_URL = os.getenv("INFERENCE_API_URL", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "nomic-embed-text")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
INFERENCE_SKIP_PULL = os.getenv("INFERENCE_SKIP_PULL", "0").lower() in (
    "1",
    "true",
    "yes",
)
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "full").lower()

# Cloud: gateway injects account id; kernel rejects direct public access when enabled.
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "0").lower() in ("1", "true", "yes")
DEFAULT_GATEWAY_SECRET = "changeme_gateway_secret"
GATEWAY_SECRET = os.getenv("GATEWAY_SECRET", DEFAULT_GATEWAY_SECRET)
ACCOUNT_ID_HEADER = "X-SoulOS-Account-Id"
GATEWAY_SECRET_HEADER = "X-SoulOS-Gateway-Secret"

MEMORY_SYNC_WORKSPACE = os.getenv("SOULOS_MEMORY_SYNC_WORKSPACE", "").strip()
MEMORY_SYNC_BOT_ID = os.getenv("SOULOS_MEMORY_SYNC_BOT_ID", "").strip()

WEAK_GATEWAY_SECRETS = frozenset(
    {DEFAULT_GATEWAY_SECRET, "changeme", "secret", "password", ""}
)

engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)


def validate_gateway_secret() -> None:
    """Refuse cloud mode startup when GATEWAY_SECRET is a known weak default."""
    if not REQUIRE_AUTH:
        return
    if GATEWAY_SECRET in WEAK_GATEWAY_SECRETS:
        raise RuntimeError(
            "REQUIRE_AUTH=1 but GATEWAY_SECRET is a weak default value. "
            "Set a strong GATEWAY_SECRET before running in cloud mode."
        )
