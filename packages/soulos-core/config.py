"""SoulOS kernel configuration from environment."""

import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:changeme_local_dev@db:5432/soulos",
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
# Shared secret for inference bridge /api/* when BRIDGE_AUTH_TOKEN is set on the bridge.
INFERENCE_BRIDGE_TOKEN = (
    os.getenv("INFERENCE_BRIDGE_TOKEN", "").strip()
    or os.getenv("BRIDGE_AUTH_TOKEN", "").strip()
)


def inference_headers() -> dict[str, str]:
    """Authorization headers for the Ollama-compatible inference plug-in."""
    if not INFERENCE_BRIDGE_TOKEN:
        return {}
    return {"Authorization": f"Bearer {INFERENCE_BRIDGE_TOKEN}"}

# Cloud: gateway injects account id; kernel rejects direct public access when enabled.
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "0").lower() in ("1", "true", "yes")
DEFAULT_GATEWAY_SECRET = "changeme_gateway_secret"
GATEWAY_SECRET = os.getenv("GATEWAY_SECRET", DEFAULT_GATEWAY_SECRET)
ACCOUNT_ID_HEADER = "X-SoulOS-Account-Id"
GATEWAY_SECRET_HEADER = "X-SoulOS-Gateway-Secret"

MEMORY_SYNC_WORKSPACE = os.getenv("SOULOS_MEMORY_SYNC_WORKSPACE", "").strip()
MEMORY_SYNC_BOT_ID = os.getenv("SOULOS_MEMORY_SYNC_BOT_ID", "").strip()
# Session-scoped episodic rows older than this are excluded from retrieve and
# deletable via POST /memory/purge-expired. 0 disables TTL.
MEMORY_SESSION_TTL_SECONDS = int(os.getenv("MEMORY_SESSION_TTL_SECONDS", "0"))
# Max characters for memory content / hybrid summary (and related text fields).
MAX_MEMORY_CONTENT_CHARS = int(os.getenv("MAX_MEMORY_CONTENT_CHARS", "32768"))

# Hybrid retrieval (dense + FTS → cutoff → RRF → importance → MMR)
MEMORY_RETRIEVAL_MODE = os.getenv("MEMORY_RETRIEVAL_MODE", "hybrid").lower()
MEMORY_MAX_DISTANCE = float(os.getenv("MEMORY_MAX_DISTANCE", "0.85"))
MEMORY_MMR_LAMBDA = float(os.getenv("MEMORY_MMR_LAMBDA", "0.7"))
MEMORY_MMR_CANDIDATE_CAP = int(os.getenv("MEMORY_MMR_CANDIDATE_CAP", "24"))
MEMORY_RRF_K = int(os.getenv("MEMORY_RRF_K", "60"))
MEMORY_IMPORTANCE_WEIGHT = float(os.getenv("MEMORY_IMPORTANCE_WEIGHT", "0.25"))
MEMORY_DENSE_CANDIDATE_LIMIT = int(os.getenv("MEMORY_DENSE_CANDIDATE_LIMIT", "40"))
MEMORY_LEXICAL_CANDIDATE_LIMIT = int(os.getenv("MEMORY_LEXICAL_CANDIDATE_LIMIT", "40"))

# MSV reflect constraints
MSV_EMA_ALPHA = float(os.getenv("MSV_EMA_ALPHA", "0.25"))
MSV_MAX_STEP = float(os.getenv("MSV_MAX_STEP", "0.15"))
MSV_EMA_MIN_CONFIDENCE = float(os.getenv("MSV_EMA_MIN_CONFIDENCE", "0.60"))
MSV_UNCERTAINTY_FLOOR = float(os.getenv("MSV_UNCERTAINTY_FLOOR", "0.05"))
MSV_UNCERTAINTY_DECAY = float(os.getenv("MSV_UNCERTAINTY_DECAY", "0.7"))
MSV_RETRIEVAL_UNCERTAINTY_NUDGE = float(
    os.getenv("MSV_RETRIEVAL_UNCERTAINTY_NUDGE", "0.05")
)

# Dual-process router
DEFAULT_UNCERTAINTY_TRIGGER = float(os.getenv("DEFAULT_UNCERTAINTY_TRIGGER", "0.7"))
SOULOS_ROUTER_LOG_PATH = os.getenv("SOULOS_ROUTER_LOG_PATH", "").strip()

# Hybrid prepare multi-source memory budgets (fractions, sum ≈ 1)
MEMORY_BUDGET_EPISODIC = float(os.getenv("MEMORY_BUDGET_EPISODIC", "0.4"))
MEMORY_BUDGET_SHARED = float(os.getenv("MEMORY_BUDGET_SHARED", "0.4"))
MEMORY_BUDGET_SEMANTIC = float(os.getenv("MEMORY_BUDGET_SEMANTIC", "0.2"))

# Capability query cache TTL (seconds)
CAPABILITY_CACHE_TTL_SECONDS = float(os.getenv("CAPABILITY_CACHE_TTL_SECONDS", "30"))

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
