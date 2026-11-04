"""Strict identifier and MCP resource URI validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

# UUID or opaque bot ids used in tests (alphanumeric + hyphen/underscore).
_BOT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")


class McpIdError(ValueError):
    """Raised when an MCP identifier or URI fails validation."""


def validate_bot_id(bot_id: str | None) -> str:
    if not bot_id or not isinstance(bot_id, str):
        raise McpIdError("bot_id is required")
    raw = bot_id.strip()
    decoded = unquote(raw)
    if raw != decoded and any(m in raw.lower() for m in ("%2e", "%2f", "%5c")):
        raise McpIdError("bot_id must not contain encoded path segments")
    if any(m in decoded for m in ("/", "\\", "..")):
        raise McpIdError("bot_id must not contain path segments")
    if not _BOT_ID_RE.match(decoded):
        raise McpIdError("bot_id has invalid format")
    return decoded


def validate_session_id(session_id: str | None, *, required: bool = True) -> str | None:
    if session_id is None or session_id == "":
        if required:
            raise McpIdError("session_id is required")
        return None
    if not isinstance(session_id, str):
        raise McpIdError("session_id must be a string")
    raw = session_id.strip()
    decoded = unquote(raw)
    lower = raw.lower()
    if any(m in lower for m in ("%2e%2e", "%2e.", ".%2e", "%2f", "%5c")):
        raise McpIdError("session_id must not contain encoded path segments")
    if ".." in decoded or "/" in decoded or "\\" in decoded:
        raise McpIdError("session_id must not contain path segments")
    if not _SESSION_ID_RE.match(decoded):
        raise McpIdError("session_id has invalid format")
    return decoded


@dataclass(frozen=True)
class ParsedResourceUri:
    scheme: str
    kind: str
    bot_id: str | None = None
    session_id: str | None = None
    limit: int | None = None


def parse_resource_uri(
    uri: str, *, default_episodic_limit: int = 50, max_limit: int = 100
) -> ParsedResourceUri:
    if not uri or not isinstance(uri, str):
        raise McpIdError("resource URI is required")

    path_only = uri.split("?", 1)[0]
    decoded_path = unquote(path_only)
    if ".." in decoded_path or "%2e" in path_only.lower():
        raise McpIdError("resource URI must not contain path traversal")
    if "*" in path_only:
        raise McpIdError("resource URI must not contain wildcards")

    parsed = urlparse(uri)
    scheme = (parsed.scheme or "").lower()
    path = parsed.path or ""
    netloc = parsed.netloc or ""
    parts = ([netloc] if netloc else []) + [p for p in path.split("/") if p]

    limit = default_episodic_limit
    if parsed.query:
        for pair in parsed.query.split("&"):
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            if k == "limit":
                try:
                    limit = int(v)
                except ValueError as e:
                    raise McpIdError("limit must be an integer") from e
                if limit < 1 or limit > max_limit:
                    raise McpIdError(f"limit must be between 1 and {max_limit}")

    if scheme == "memory" and parts and parts[0] == "episodic":
        if len(parts) != 2:
            raise McpIdError("memory://episodic/{bot_id} requires exactly one bot_id")
        return ParsedResourceUri(
            scheme="memory",
            kind="episodic",
            bot_id=validate_bot_id(parts[1]),
            limit=limit,
        )
    if scheme == "soul" and parts and parts[0] == "identity":
        if len(parts) != 2:
            raise McpIdError("soul://identity/{bot_id} requires exactly one bot_id")
        return ParsedResourceUri(
            scheme="soul", kind="identity", bot_id=validate_bot_id(parts[1])
        )
    if scheme == "soul" and parts == ["schema"]:
        return ParsedResourceUri(scheme="soul", kind="schema")
    if scheme == "msv" and parts and parts[0] == "drift":
        if len(parts) != 2:
            raise McpIdError("msv://drift/{bot_id} requires exactly one bot_id")
        return ParsedResourceUri(
            scheme="msv", kind="drift", bot_id=validate_bot_id(parts[1])
        )
    if scheme == "session" and parts and parts[0] == "turn":
        if len(parts) != 3:
            raise McpIdError(
                "session://turn/{bot_id}/{session_id} requires bot_id and session_id"
            )
        return ParsedResourceUri(
            scheme="session",
            kind="turn",
            bot_id=validate_bot_id(parts[1]),
            session_id=validate_session_id(parts[2]),
        )
    raise McpIdError(f"Unknown or invalid resource URI: {uri}")
