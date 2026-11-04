"""Log filter that redacts Authorization / bearer tokens from log records."""

from __future__ import annotations

import logging
import re

_BEARER = re.compile(r"(?i)(authorization[\"'=\s:]+bearer\s+)([a-z0-9._\-]+)")
_ENV_SECRET = re.compile(
    r"(?i)((?:api[_-]?key|token|secret|password)[\"'=\s:]+)([^\s\"']{8,})"
)


class SecretRedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = _BEARER.sub(r"\1[REDACTED]", msg)
        redacted = _ENV_SECRET.sub(r"\1[REDACTED]", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def install_secret_redact_filter() -> None:
    filt = SecretRedactFilter()
    root = logging.getLogger()
    if not any(isinstance(f, SecretRedactFilter) for f in root.filters):
        root.addFilter(filt)
    for name in ("mcp_client", "mcp_server", "uvicorn", "uvicorn.error"):
        logging.getLogger(name).addFilter(filt)
