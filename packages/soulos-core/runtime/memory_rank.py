"""Hybrid retrieval ranking: cutoff → RRF → importance boost → capped cosine MMR."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence


@dataclass
class MemoryHit:
    """Structured retrieval hit with optional score components."""

    content: str
    id: str | None = None
    dense_distance: float | None = None
    fts_rank: float | None = None
    rrf_score: float | None = None
    importance: float = 0.5
    memory_kind: str = "episodic"
    source: str = "bot"  # bot | shared | semantic
    embedding: list[float] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("embedding", None)
        return d

    def __str__(self) -> str:
        return self.content


def hit_contents(hits: Sequence[MemoryHit]) -> list[str]:
    return [h.content for h in hits]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def apply_distance_cutoff(
    candidates: list[MemoryHit], max_distance: float
) -> list[MemoryHit]:
    """Keep dense hits with distance <= max_distance. Hits without distance pass."""
    out: list[MemoryHit] = []
    for hit in candidates:
        if hit.dense_distance is None:
            out.append(hit)
        elif hit.dense_distance <= max_distance:
            out.append(hit)
    return out


def reciprocal_rank_fusion(
    dense_ranked: list[MemoryHit],
    lexical_ranked: list[MemoryHit],
    *,
    k: int = 60,
    importance_weight: float = 0.25,
) -> list[MemoryHit]:
    """Fuse dense and lexical lists with RRF, then multiply by importance factor."""
    scores: dict[str, float] = {}
    by_key: dict[str, MemoryHit] = {}

    def _key(hit: MemoryHit, idx: int) -> str:
        return hit.id if hit.id else f"content:{hit.content}:{idx}"

    for rank, hit in enumerate(dense_ranked):
        key = _key(hit, rank)
        by_key[key] = hit
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)

    for rank, hit in enumerate(lexical_ranked):
        key = _key(hit, rank)
        if key not in by_key:
            by_key[key] = hit
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)

    fused: list[MemoryHit] = []
    for key, rrf in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
        hit = by_key[key]
        importance = max(0.0, min(1.0, float(hit.importance)))
        hit.rrf_score = rrf * (1.0 + importance * importance_weight)
        fused.append(hit)
    fused.sort(key=lambda h: h.rrf_score or 0.0, reverse=True)
    return fused


def mmr_select(
    candidates: list[MemoryHit],
    *,
    top_k: int,
    lambda_mult: float = 0.7,
    candidate_cap: int = 24,
    query_embedding: Sequence[float] | None = None,
) -> list[MemoryHit]:
    """Maximal Marginal Relevance using cosine similarity; caps candidate pool."""
    if top_k <= 0 or not candidates:
        return []
    pool = candidates[: max(1, candidate_cap)]
    if len(pool) <= top_k:
        return pool

    # Prefer query similarity via dense distance when no embedding on hit
    def relevance(hit: MemoryHit) -> float:
        if hit.rrf_score is not None:
            return float(hit.rrf_score)
        if hit.dense_distance is not None:
            return 1.0 / (1.0 + float(hit.dense_distance))
        return 0.0

    selected: list[MemoryHit] = []
    remaining = list(pool)

    while remaining and len(selected) < top_k:
        best_idx = 0
        best_score = float("-inf")
        for i, cand in enumerate(remaining):
            rel = relevance(cand)
            if not selected:
                score = rel
            else:
                max_sim = 0.0
                for prev in selected:
                    if cand.embedding and prev.embedding:
                        max_sim = max(
                            max_sim, cosine_similarity(cand.embedding, prev.embedding)
                        )
                    elif query_embedding and cand.embedding:
                        # fall back: diversity via query-aligned cosine only if both embed
                        pass
                score = lambda_mult * rel - (1.0 - lambda_mult) * max_sim
            if score > best_score:
                best_score = score
                best_idx = i
        selected.append(remaining.pop(best_idx))
    return selected


def sanitize_websearch_query(query: str) -> str | None:
    """Return a safe query string for websearch_to_tsquery, or None to skip FTS."""
    q = (query or "").strip()
    if not q:
        return None
    # Truncate extremes; websearch_to_tsquery tolerates punctuation better than plainto
    if len(q) > 512:
        q = q[:512]
    return q
