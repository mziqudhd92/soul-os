"""Unit tests for hybrid memory ranking."""

from runtime.memory_rank import (
    MemoryHit,
    apply_distance_cutoff,
    mmr_select,
    reciprocal_rank_fusion,
    sanitize_websearch_query,
)


def test_sanitize_allows_punctuation():
    assert sanitize_websearch_query("refund: policy! & returns|") is not None
    assert sanitize_websearch_query("   ") is None


def test_distance_cutoff_before_rrf():
    hits = [
        MemoryHit(content="a", id="1", dense_distance=0.2),
        MemoryHit(content="b", id="2", dense_distance=0.9),
        MemoryHit(content="c", id="3", dense_distance=0.5),
    ]
    kept = apply_distance_cutoff(hits, 0.85)
    assert [h.id for h in kept] == ["1", "3"]


def test_rrf_importance_boost():
    dense = [
        MemoryHit(content="a", id="1", dense_distance=0.1, importance=0.1),
        MemoryHit(content="b", id="2", dense_distance=0.2, importance=1.0),
    ]
    lexical = [
        MemoryHit(content="b", id="2", fts_rank=0.9, importance=1.0),
        MemoryHit(content="a", id="1", fts_rank=0.5, importance=0.1),
    ]
    fused = reciprocal_rank_fusion(dense, lexical, k=60, importance_weight=1.0)
    assert fused[0].id == "2"
    assert fused[0].rrf_score is not None


def test_mmr_caps_candidates():
    cands = [
        MemoryHit(
            content=f"m{i}",
            id=str(i),
            rrf_score=1.0 / (i + 1),
            embedding=[float(i), 0.0, 0.0],
        )
        for i in range(40)
    ]
    selected = mmr_select(cands, top_k=5, candidate_cap=10, lambda_mult=0.7)
    assert len(selected) == 5
    # Only first 10 of pool considered
    assert all(int(h.id) < 10 for h in selected)
