"""Compile unified .soul (YAML front matter + Markdown) to soul dict."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from soul_validation import default_msv_dict

FRONT_MATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", re.DOTALL)

HEXACO_LONG_TO_SHORT: dict[str, str] = {
    "honesty_humility": "H",
    "honesty-humility": "H",
    "emotionality": "E",
    "extraversion": "X",
    "agreeableness": "A",
    "conscientiousness": "C",
    "openness": "O",
}
HEXACO_SHORT = frozenset("HEXACO")

PHASE2_TOP_LEVEL = frozenset({"id", "version", "engine", "dual_process"})
PHASE2_PSYCHOLOGY = frozenset({"dual_process"})

DEFAULT_DUAL_PROCESS = {
    "system1_threshold": 0.35,
    "system2_max_loops": 3,
}

MORAL_KEYS = (
    "care_harm",
    "fairness_cheating",
    "loyalty_betrayal",
    "authority_subversion",
    "sanctity_degradation",
)
DRIVE_KEYS = ("curiosity", "autonomy", "social_approval")


def extract_runtime_config(fm: dict[str, Any]) -> dict[str, Any]:
    """Extract engine + dual_process from front matter (Phase 2 runtime config)."""
    runtime: dict[str, Any] = {}
    if isinstance(fm.get("engine"), dict):
        runtime["engine"] = dict(fm["engine"])
    dual: dict[str, Any] = dict(DEFAULT_DUAL_PROCESS)
    if isinstance(fm.get("dual_process"), dict):
        dual.update(fm["dual_process"])
    psychology = fm.get("psychology")
    if isinstance(psychology, dict) and isinstance(psychology.get("dual_process"), dict):
        dual.update(psychology["dual_process"])
    runtime["dual_process"] = dual
    return runtime


def _strip_phase2_front_matter(fm: dict[str, Any]) -> dict[str, Any]:
    cleaned = {k: v for k, v in fm.items() if k not in PHASE2_TOP_LEVEL}
    psychology = cleaned.get("psychology")
    if isinstance(psychology, dict):
        cleaned["psychology"] = {
            k: v for k, v in psychology.items() if k not in PHASE2_PSYCHOLOGY
        }
    return cleaned


def _map_hexaco(hexaco_raw: dict[str, Any] | None) -> dict[str, float]:
    if not hexaco_raw:
        return {}
    mapped: dict[str, float] = {}
    for key, value in hexaco_raw.items():
        short = key if key in HEXACO_SHORT else HEXACO_LONG_TO_SHORT.get(key.lower())
        if short and short not in mapped:
            mapped[short] = float(value)
    return mapped


def _merge_moral_foundations(
    raw: dict[str, Any] | None, defaults: dict[str, Any]
) -> dict[str, float]:
    base = dict(defaults.get("moral_foundations") or {})
    if raw:
        for key in MORAL_KEYS:
            if key in raw:
                base[key] = float(raw[key])
    return base


def _merge_drives(raw: dict[str, Any] | None, defaults: dict[str, Any]) -> dict[str, float]:
    base = dict(defaults.get("drives") or {})
    if raw:
        for key in DRIVE_KEYS:
            if key in raw:
                base[key] = float(raw[key])
    return base


def _build_baseline_msv(psychology: dict[str, Any] | None) -> dict[str, Any]:
    defaults = default_msv_dict()
    psych = psychology or {}
    hexaco_raw = _map_hexaco(psych.get("hexaco"))
    default_hexaco = defaults["hexaco"]
    hexaco = {k: hexaco_raw.get(k, default_hexaco[k]) for k in "HEXACO"}

    epistemic = psych.get("epistemic_uncertainty", defaults["epistemic_uncertainty"])
    inner = psych.get("inner_monologue", defaults["inner_monologue"])

    return {
        "hexaco": hexaco,
        "moral_foundations": _merge_moral_foundations(
            psych.get("moral_foundations"), defaults
        ),
        "drives": _merge_drives(psych.get("drives"), defaults),
        "epistemic_uncertainty": float(epistemic),
        "inner_monologue": str(inner).strip() or defaults["inner_monologue"],
    }


def _front_matter_to_payload(fm: dict[str, Any], body: str) -> dict[str, Any]:
    fm = _strip_phase2_front_matter(fm)
    psychology = fm.pop("psychology", None)
    if not isinstance(psychology, dict):
        psychology = {}

    description = body.strip()
    if not description:
        raise ValueError(".soul markdown body (description) must not be empty")

    payload: dict[str, Any] = {
        "name": str(fm.get("name", "")).strip(),
        "role": str(fm.get("role", "")).strip(),
        "description": description,
        "attachment_style": str(fm.get("attachment_style", "Secure")).strip(),
        "baseline_msv": _build_baseline_msv(psychology),
    }

    for optional in ("status", "capabilities", "hourly_rate", "avatar_url"):
        if optional in fm and fm[optional] is not None:
            payload[optional] = fm[optional]

    if not payload["name"]:
        raise ValueError(".soul front matter: missing required field 'name'")
    if not payload["role"]:
        raise ValueError(".soul front matter: missing required field 'role'")

    return payload


def compile_soul_bundle(
    text: str, filename_hint: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse .soul text into soul dict and runtime_config."""
    del filename_hint  # reserved for future diagnostics
    normalized = text.lstrip("\ufeff")
    match = FRONT_MATTER_RE.match(normalized)
    if not match:
        raise ValueError(
            ".soul file must start with YAML front matter delimited by --- lines"
        )

    yaml_block, body = match.group(1), match.group(2)
    try:
        fm = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise ValueError(f".soul YAML front matter parse error: {exc}") from exc

    if not isinstance(fm, dict):
        raise ValueError(".soul front matter must be a YAML mapping")

    runtime_config = extract_runtime_config(fm)
    return _front_matter_to_payload(fm, body), runtime_config


def compile_soul_text(text: str, filename_hint: str | None = None) -> dict[str, Any]:
    """Parse .soul text (YAML front matter + Markdown body) into a soul dict."""
    payload, _ = compile_soul_bundle(text, filename_hint=filename_hint)
    return payload


def compile_soul_bytes(data: bytes, filename_hint: str | None = None) -> dict[str, Any]:
    """Decode bytes and compile as .soul text."""
    text = data.decode("utf-8")
    return compile_soul_text(text, filename_hint=filename_hint)


def _looks_like_json(raw: bytes) -> bool:
    stripped = raw.lstrip()
    return stripped.startswith(b"{") or stripped.startswith(b"[")


def _looks_like_soul(raw: bytes) -> bool:
    return raw.lstrip(b"\ufeff").startswith(b"---")


def _hint_is_soul(filename_hint: str | None) -> bool:
    if not filename_hint:
        return False
    lower = filename_hint.lower()
    return lower.endswith(".soul") and not lower.endswith(".soul.json")


def normalize_runtime_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    runtime: dict[str, Any] = {"dual_process": dict(DEFAULT_DUAL_PROCESS)}
    if not raw:
        return runtime
    if isinstance(raw.get("dual_process"), dict):
        runtime["dual_process"].update(raw["dual_process"])
    if isinstance(raw.get("engine"), dict):
        runtime["engine"] = dict(raw["engine"])
    return runtime


def split_registration_payload(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate soul fields from optional runtime_config for registration."""
    payload = dict(data)
    runtime_raw = payload.pop("runtime_config", None)
    runtime_config = (
        normalize_runtime_config(runtime_raw)
        if isinstance(runtime_raw, dict)
        else normalize_runtime_config(None)
    )
    return payload, runtime_config


def parse_soul_request_bundle(
    raw: bytes,
    content_type: str,
    filename_hint: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse HTTP request body as JSON or compiled .soul with runtime_config."""
    ct = (content_type or "").split(";")[0].strip().lower()

    if ct == "application/json" or _looks_like_json(raw):
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid JSON soul payload: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Soul JSON payload must be an object")
        return split_registration_payload(data)

    if _hint_is_soul(filename_hint) or _looks_like_soul(raw):
        text = raw.decode("utf-8")
        return compile_soul_bundle(text, filename_hint=filename_hint)

    errors: list[str] = []
    try:
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            return split_registration_payload(data)
        errors.append("JSON payload must be an object")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"JSON: {exc}")

    try:
        text = raw.decode("utf-8")
        return compile_soul_bundle(text, filename_hint=filename_hint)
    except ValueError as exc:
        errors.append(f".soul: {exc}")
        raise ValueError(
            "Could not parse soul payload as JSON or .soul:\n"
            + "\n".join(f"  • {line}" for line in errors)
        ) from exc


def parse_soul_request_payload(
    raw: bytes,
    content_type: str,
    filename_hint: str | None = None,
) -> dict[str, Any]:
    """Parse HTTP request body as JSON or compiled .soul."""
    payload, _ = parse_soul_request_bundle(raw, content_type, filename_hint)
    return payload


def load_soul_path(path: Path) -> dict[str, Any]:
    """Load and parse a .soul or .soul.json file from disk."""
    data = path.read_bytes()
    name = path.name.lower()
    if name.endswith(".soul.json"):
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: soul JSON must be an object")
        return payload
    if name.endswith(".soul"):
        return compile_soul_bytes(data, filename_hint=path.name)
    raise ValueError(f"Unsupported soul file extension: {path.suffix}")
