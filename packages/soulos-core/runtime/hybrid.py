"""Hybrid sidecar helpers: prompt building and turn orchestration."""

from __future__ import annotations

from typing import Any

from runtime.cognitive_telemetry import merge_runtime_config
from runtime.trait_directives import compile_trait_directives

DEFAULT_HYBRID_TEMPLATE = (
    "You are {name}, {role}.\n"
    "{description}\n"
    "Behavior directives:\n{trait_directives}\n"
    "Inner state: {inner_monologue}\n"
    "Recalled memories:\n{memories}"
)


def format_memory_block(memories: list[str]) -> str:
    if not memories:
        return "(none)"
    return "\n".join(f"- {m}" for m in memories)


def apply_memory_budgets(
    episodic: list[str],
    shared: list[str],
    semantic: list[str],
    *,
    top_k: int,
    budget_episodic: float = 0.4,
    budget_shared: float = 0.4,
    budget_semantic: float = 0.2,
) -> list[str]:
    """Allocate slots across sources; preserve order within each bucket."""
    if top_k <= 0:
        return []
    total = budget_episodic + budget_shared + budget_semantic
    if total <= 0:
        return (episodic + shared + semantic)[:top_k]
    n_ep = int(round(top_k * budget_episodic / total))
    n_sh = int(round(top_k * budget_shared / total))
    n_se = max(0, top_k - n_ep - n_sh)
    # Ensure we fill top_k if one bucket is empty
    picked = episodic[:n_ep] + shared[:n_sh] + semantic[:n_se]
    if len(picked) < top_k:
        rest = episodic[n_ep:] + shared[n_sh:] + semantic[n_se:]
        for item in rest:
            if len(picked) >= top_k:
                break
            if item not in picked:
                picked.append(item)
    return picked[:top_k]


def build_hybrid_system_prompt(
    identity: dict[str, Any],
    memories: list[str],
    runtime_config: dict[str, Any] | None = None,
) -> str:
    cfg = merge_runtime_config(runtime_config)
    template = cfg.get("hybrid_prompt_template") or DEFAULT_HYBRID_TEMPLATE
    msv = identity.get("current_msv") or {}
    inner = msv.get("inner_monologue", "")
    if isinstance(inner, str) and len(inner) > 240:
        inner = inner[:240]
    traits = compile_trait_directives(msv if isinstance(msv, dict) else {})
    values = {
        "name": identity.get("name", "Assistant"),
        "role": identity.get("role", "assistant"),
        "description": identity.get("description", ""),
        "inner_monologue": inner,
        "memories": format_memory_block(memories),
        "trait_directives": traits or "(none)",
    }
    try:
        return template.format(**values)
    except KeyError:
        # Custom templates may omit trait_directives
        safe = {
            k: v
            for k, v in values.items()
            if f"{{{k}}}" in template or k in ("name", "role", "description", "inner_monologue", "memories")
        }
        # Prefer format_map with defaults
        class _Default(dict):
            def __missing__(self, key: str) -> str:
                return values.get(key, "")

        return template.format_map(_Default(values))


def extract_inner_monologue(identity: dict[str, Any]) -> str:
    msv = identity.get("current_msv") or {}
    return str(msv.get("inner_monologue", ""))
