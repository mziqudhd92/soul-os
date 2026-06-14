"""`.soulignore` pattern matching and secret blocking for memory ledger."""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
]


def load_soulignore_patterns(workspace_root: Path) -> list[str]:
    path = workspace_root / ".soulignore"
    if not path.is_file():
        return []
    patterns: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)
    return patterns


def is_ignored_path(rel_path: str, patterns: list[str]) -> bool:
    normalized = rel_path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch(normalized, pattern) or fnmatch(normalized, f"**/{pattern}"):
            return True
    return False


def content_matches_ignore_patterns(content: str, patterns: list[str]) -> bool:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in patterns:
            if is_ignored_path(stripped, [pattern]):
                return True
            if "*" not in pattern and "/" not in pattern and pattern in stripped:
                return True
    return False


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def validate_memory_content(content: str, workspace_root: Path | None = None) -> None:
    if contains_secret(content):
        raise ValueError(
            "Memory content blocked: possible secret detected by .soulignore scanner"
        )
    if workspace_root is not None:
        patterns = load_soulignore_patterns(workspace_root)
        if patterns and content_matches_ignore_patterns(content, patterns):
            raise ValueError("Memory content blocked by .soulignore pattern match")
