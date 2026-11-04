"""Persona-aware retrieval re-ranking (recency + mood-congruent)."""

from __future__ import annotations

from typing import Any

from runtime.memory_rank import MemoryHit
from runtime.msv_update import HEXACO_KEYS, clamp_msv

_MOOD_LEXICON: dict[str, tuple[str, ...]] = {
    "E": ("anxious", "afraid", "upset", "stress", "hurt", "cry", "worry", "fear"),
    "A": ("kind", "together", "sorry", "please", "thanks", "help", "care"),
    "X": ("excited", "party", "fun", "chat", "social", "hello", "meet"),
    "C": ("plan", "deadline", "checklist", "must", "schedule", "organize"),
    "O": ("idea", "curious", "wonder", "creative", "explore", "new"),
    "H": ("honest", "fair", "truth", "promise", "sincere"),
}


def _mood_boost(content: str, current_msv: dict[str, Any]) -> float:
    """Small multiplicative boost when content aligns with elevated HEXACO traits."""
    msv = clamp_msv(current_msv)
    hexaco = msv.get("hexaco") or {}
    text = (content or "").lower()
    boost = 0.0
    for key in HEXACO_KEYS:
        level = float(hexaco.get(key, 0.0))
        if abs(level) < 0.15:
            continue
        tokens = _MOOD_LEXICON.get(key, ())
        hits = sum(1 for t in tokens if t in text)
        if hits and level > 0:
            boost += 0.15 * hits * level
        elif hits and level < 0:
            boost -= 0.08 * hits * abs(level)
    return max(-0.25, min(0.75, boost))


def rerank_hits_for_persona(
    hits: list[MemoryHit],
    *,
    top_k: int,
    recency_weight: float = 0.0,
    mood_congruent: bool = False,
    current_msv: dict[str, Any] | None = None,
) -> list[MemoryHit]:
    """Re-rank hybrid hits with optional recency blend and mood congruence."""
    if not hits:
        return []
    rw = max(0.0, min(1.0, float(recency_weight or 0.0)))
    n = len(hits)
    scored: list[tuple[float, MemoryHit]] = []
    for i, hit in enumerate(hits):
        base = float(hit.rrf_score) if hit.rrf_score is not None else 1.0 / (i + 1)
        # Without created_at on hits, treat earlier list positions from dense/hybrid
        # as more "recently relevant"; callers pass hits already relevance-ordered.
        recency = 1.0 - (i / max(n, 1))
        score = (1.0 - rw) * base + rw * recency
        if mood_congruent and current_msv:
            score *= 1.0 + _mood_boost(hit.content, current_msv)
        scored.append((score, hit))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [h for _, h in scored[: max(1, top_k)]]


def strip_control_chars(text: str) -> str:
    return "".join(ch for ch in text if ch == "\n" or ord(ch) >= 32)
