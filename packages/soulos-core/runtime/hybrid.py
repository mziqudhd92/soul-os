"""Hybrid sidecar helpers: prompt building and turn orchestration."""

from __future__ import annotations

from typing import Any

from runtime.cognitive_telemetry import merge_runtime_config

DEFAULT_HYBRID_TEMPLATE = (
    "You are {name}, {role}.\n"
    "{description}\n"
    "Inner state: {inner_monologue}\n"
    "Recalled memories:\n{memories}"
)


def format_memory_block(memories: list[str]) -> str:
    if not memories:
        return "(none)"
    return "\n".join(f"- {m}" for m in memories)


def build_hybrid_system_prompt(
    identity: dict[str, Any],
    memories: list[str],
    runtime_config: dict[str, Any] | None = None,
) -> str:
    cfg = merge_runtime_config(runtime_config)
    template = cfg.get("hybrid_prompt_template") or DEFAULT_HYBRID_TEMPLATE
    msv = identity.get("current_msv") or {}
    inner = msv.get("inner_monologue", "")
    return template.format(
        name=identity.get("name", "Assistant"),
        role=identity.get("role", "assistant"),
        description=identity.get("description", ""),
        inner_monologue=inner,
        memories=format_memory_block(memories),
    )


def extract_inner_monologue(identity: dict[str, Any]) -> str:
    msv = identity.get("current_msv") or {}
    return str(msv.get("inner_monologue", ""))
