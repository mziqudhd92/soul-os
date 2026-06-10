"""SoulOS Cloud gateway configuration."""

import os

KERNEL_URL = os.getenv("KERNEL_URL", "http://soulos-kernel:8000").rstrip("/")
GATEWAY_SECRET = os.getenv("GATEWAY_SECRET", "changeme_gateway_secret")
KEYS_FILE = os.getenv("SOULOS_KEYS_FILE", "keys.json")
API_KEYS_JSON = os.getenv("SOULOS_API_KEYS", "")
DEFAULT_RATE_LIMIT_PER_MINUTE = int(os.getenv("DEFAULT_RATE_LIMIT_PER_MINUTE", "120"))
ACCOUNT_ID_HEADER = "X-SoulOS-Account-Id"
GATEWAY_SECRET_HEADER = "X-SoulOS-Gateway-Secret"
