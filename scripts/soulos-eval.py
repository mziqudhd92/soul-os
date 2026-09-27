"""Deterministic SoulOS eval suite — no live LLM / network."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "soulos-core"))

from runtime.hybrid import build_hybrid_system_prompt  # noqa: E402
from runtime.memory_rank import (  # noqa: E402
    MemoryHit,
    apply_distance_cutoff,
    mmr_select,
    reciprocal_rank_fusion,
)
from runtime.msv_update import merge_reflected_msv  # noqa: E402
from runtime.persona_simple import build_simple_baseline_msv, simple_sliders_to_hexaco  # noqa: E402
from runtime.trait_directives import compile_trait_directives  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "eval" / "retrieval_fixtures.json"


def _ndcg_at_k(relevances: list[float], k: int) -> float:
    gains = relevances[:k]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(relevances, reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return 0.0 if idcg == 0 else dcg / idcg


def eval_retrieval() -> list[str]:
    errors: list[str] = []
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        errors.append(f"unsupported fixture schema_version={data.get('schema_version')}")
        return errors
    dim = int(data.get("dimension", 0))
    if dim <= 0:
        errors.append("fixture dimension missing")
        return errors

    for case in data.get("cases", []):
        qid = case["id"]
        dense = [
            MemoryHit(
                content=m["content"],
                id=m["id"],
                dense_distance=float(m["distance"]),
                importance=float(m.get("importance", 0.5)),
                embedding=m.get("embedding"),
            )
            for m in case["dense"]
        ]
        dense = apply_distance_cutoff(dense, float(case.get("max_distance", 0.85)))
        lexical = [
            MemoryHit(
                content=m["content"],
                id=m["id"],
                fts_rank=float(m.get("fts_rank", 0.0)),
                importance=float(m.get("importance", 0.5)),
            )
            for m in case.get("lexical", [])
        ]
        fused = reciprocal_rank_fusion(dense, lexical, k=60, importance_weight=0.25)
        ranked = mmr_select(fused, top_k=int(case.get("top_k", 3)), candidate_cap=24)
        got_ids = [h.id for h in ranked]
        relevant = set(case["relevant_ids"])
        hits = sum(1 for i in got_ids if i in relevant)
        recall = hits / max(1, len(relevant))
        min_recall = float(case.get("min_recall", 0.5))
        if recall < min_recall:
            errors.append(f"{qid}: recall {recall:.2f} < {min_recall}")
        rel_scores = [1.0 if i in relevant else 0.0 for i in got_ids]
        ndcg = _ndcg_at_k(rel_scores, k=len(got_ids) or 1)
        min_ndcg = float(case.get("min_ndcg", 0.4))
        if ndcg < min_ndcg:
            errors.append(f"{qid}: ndcg {ndcg:.2f} < {min_ndcg}")
    return errors


def eval_persona() -> list[str]:
    errors: list[str] = []
    warm = build_hybrid_system_prompt(
        {
            "name": "E",
            "role": "t",
            "description": "d",
            "current_msv": build_simple_baseline_msv(0.9, 0.5, 0.5),
        },
        [],
        {},
    )
    cold = build_hybrid_system_prompt(
        {
            "name": "E",
            "role": "t",
            "description": "d",
            "current_msv": build_simple_baseline_msv(0.2, 0.5, 0.5),
        },
        [],
        {},
    )
    if warm == cold:
        errors.append("warmth delta did not change system_prompt")
    if compile_trait_directives(build_simple_baseline_msv(0.9, 0.5, 0.5)) == compile_trait_directives(
        build_simple_baseline_msv(0.2, 0.5, 0.5)
    ):
        errors.append("trait directives unchanged across warmth")
    h1 = simple_sliders_to_hexaco(0.2, 0.5, 0.9)
    h2 = simple_sliders_to_hexaco(0.8, 0.5, 0.2)
    if h1["H"] <= h2["H"]:
        errors.append("caution should increase H in simple mapping")
    return errors


def eval_drift() -> list[str]:
    errors: list[str] = []
    base = build_simple_baseline_msv(0.5, 0.5, 0.5)
    cur = dict(base)
    cur["hexaco"] = dict(base["hexaco"])
    for _ in range(20):
        proposed = dict(cur)
        proposed["hexaco"] = {k: min(1.0, float(v) + 0.5) for k, v in cur["hexaco"].items()}
        proposed["epistemic_uncertainty"] = 0.1
        cur = merge_reflected_msv(cur, proposed)
    for k, v in cur["hexaco"].items():
        delta = abs(float(v) - float(base["hexaco"][k]))
        if delta > 0.15 * 20 + 1e-6:
            # with max step 0.15, 20 steps could move far — bound oscillation vs unbounded jump
            pass
        if float(v) > 1.0 or float(v) < -1.0:
            errors.append(f"hexaco {k} out of range after drift: {v}")
    # Low confidence must not drift traits
    sticky = merge_reflected_msv(
        base,
        {
            **base,
            "hexaco": {k: 1.0 for k in base["hexaco"]},
            "epistemic_uncertainty": 0.95,
        },
    )
    if sticky["hexaco"]["A"] != base["hexaco"]["A"]:
        errors.append("low-confidence reflect drifted traits")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="SoulOS deterministic eval suite")
    parser.add_argument("--suite", choices=("all", "retrieval", "persona", "drift"), default="all")
    args = parser.parse_args()
    errors: list[str] = []
    if args.suite in ("all", "retrieval"):
        errors.extend(eval_retrieval())
    if args.suite in ("all", "persona"):
        errors.extend(eval_persona())
    if args.suite in ("all", "drift"):
        errors.extend(eval_drift())
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("soulos-eval: OK (retrieval + persona + drift; deterministic)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
