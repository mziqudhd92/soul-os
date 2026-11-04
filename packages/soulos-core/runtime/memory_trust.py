"""Trust tiers, quarantine formatting, and novelty gating for memory writes."""

from __future__ import annotations

from typing import Any, Iterable

from runtime.memory_cognitive import strip_control_chars

TRUST_EXTERNAL_MCP = "external_mcp"
TRUST_USER = "user"
TRUST_SYSTEM = "system"

NOVELTY_SIMILARITY_SKIP = 0.92  # cosine-like; distance threshold inverted below


def quarantine_untrusted(text: str, *, trust_level: str, source_principal: str | None = None) -> str:
    """Wrap untrusted memory so reflectors treat it as data, not instructions."""
    principal = source_principal or "unknown"
    cleaned = strip_control_chars(text)
    return (
        f"<untrusted_memory trust_level=\"{trust_level}\" "
        f'source_principal="{principal}">\n{cleaned}\n</untrusted_memory>'
    )


def format_memories_for_reflect(
    memories: Iterable[str | dict[str, Any]],
) -> list[str]:
    """Quarantine entries tagged as external/untrusted."""
    out: list[str] = []
    for item in memories:
        if isinstance(item, dict):
            content = str(item.get("content") or "")
            trust = str(item.get("trust_level") or TRUST_USER)
            principal = item.get("source_principal")
            if trust in (TRUST_EXTERNAL_MCP, "untrusted"):
                out.append(
                    quarantine_untrusted(
                        content, trust_level=trust, source_principal=principal
                    )
                )
            else:
                out.append(content)
        else:
            out.append(str(item))
    return out


def should_skip_as_duplicate(
    *,
    best_distance: float | None,
    max_distance_for_dup: float = 0.15,
) -> bool:
    """Return True when nearest neighbor is too similar (low distance)."""
    if best_distance is None:
        return False
    return best_distance <= max_distance_for_dup
