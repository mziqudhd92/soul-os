"""Import ClawSouls persona packages into SoulOS soul payloads."""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
import yaml

from soul_validation import default_msv_dict, validate_soul_payload

CLAWSOULS_API_BASE = os.getenv(
    "CLAWSOULS_API_BASE", "https://clawsouls.ai/api/v1"
).rstrip("/")

ALLOWED_LICENSES = frozenset(
    {
        "Apache-2.0",
        "MIT",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "CC-BY-4.0",
        "CC0-1.0",
        "ISC",
        "Unlicense",
    }
)

FILE_MERGE_KEYS = ("soul", "identity", "style", "agents", "heartbeat")
DEFAULT_MERGE_FILES = (
    "SOUL.md",
    "IDENTITY.md",
    "STYLE.md",
    "AGENTS.md",
    "HEARTBEAT.md",
)

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000027BF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "]+",
    flags=re.UNICODE,
)

_PRESETS_PATH = Path(__file__).resolve().parent / "clawsouls_presets.yaml"
_PRESETS_CACHE: dict[str, Any] | None = None


def import_enabled() -> bool:
    return os.getenv("CLAWSOULS_IMPORT_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _load_presets() -> dict[str, Any]:
    global _PRESETS_CACHE
    if _PRESETS_CACHE is None:
        with _PRESETS_PATH.open(encoding="utf-8") as fh:
            _PRESETS_CACHE = yaml.safe_load(fh) or {}
    return _PRESETS_CACHE


def clawsouls_soul_url(owner: str, name: str) -> str:
    return f"https://clawsouls.ai/en/souls/{owner}/{name}"


def manifest_author(manifest: dict[str, Any]) -> str | None:
    author = manifest.get("author")
    if isinstance(author, dict):
        name = author.get("name") or author.get("github")
        return str(name).strip() if name else None
    if isinstance(author, str) and author.strip():
        return author.strip()
    return None


def strip_emoji(text: str) -> str:
    return EMOJI_RE.sub("", text).strip()


def default_external_key(owner: str, name: str, version: str | None = None) -> str:
    base = f"clawsouls:{owner}/{name}"
    if version:
        return f"{base}@{version}"
    return base


def category_to_role(category: str | None, tags: list[str] | None) -> str:
    presets = _load_presets()
    roles = presets.get("category_roles") or {}
    if category:
        leaf = category.split("/")[-1]
        if leaf in roles:
            return roles[leaf]
        if category in roles:
            return roles[category]
    if tags:
        for tag in tags:
            if tag in roles:
                return roles[tag]
    return "AI Assistant"


def resolve_preset_name(
    manifest: dict[str, Any],
    explicit: str | None = None,
) -> str:
    if explicit:
        return explicit
    name = str(manifest.get("name") or "").strip()
    if name and name in (_load_presets().get("presets") or {}):
        return name
    if name.startswith("mbti-"):
        return "default"
    tags = manifest.get("tags") or []
    if isinstance(tags, list):
        for tag in tags:
            tag_str = str(tag).strip()
            if tag_str in (_load_presets().get("presets") or {}):
                return tag_str
    return "default"


def preset_bundle(preset_name: str) -> dict[str, Any]:
    presets = _load_presets().get("presets") or {}
    raw = presets.get(preset_name) or presets.get("default") or {}
    if not raw:
        return {
            "attachment_style": "Secure",
            "baseline_msv": default_msv_dict(),
        }
    merged = copy.deepcopy(raw)
    if "baseline_msv" not in merged:
        merged["baseline_msv"] = default_msv_dict()
    return merged


def merge_file_paths(manifest: dict[str, Any]) -> list[str]:
    files_map = manifest.get("files") or {}
    paths: list[str] = []
    if isinstance(files_map, dict):
        for key in FILE_MERGE_KEYS:
            path = files_map.get(key)
            if path and isinstance(path, str):
                paths.append(path)
    if not paths:
        paths = list(DEFAULT_MERGE_FILES)
    return paths


def merge_markdown(manifest: dict[str, Any], files: dict[str, str]) -> str:
    sections: list[str] = []
    for path in merge_file_paths(manifest):
        content = files.get(path)
        if not content or not str(content).strip():
            continue
        sections.append(str(content).strip())
    if not sections:
        one_line = str(manifest.get("description") or "").strip()
        if one_line:
            return one_line
        raise ValueError("ClawSouls bundle has no persona markdown content")
    return "\n\n---\n\n".join(sections)


def load_local_bundle(directory: Path) -> dict[str, Any]:
    root = directory.resolve()
    soul_json = root / "soul.json"
    if not soul_json.is_file():
        raise ValueError(f"Missing soul.json in {root}")
    manifest = json.loads(soul_json.read_text(encoding="utf-8"))
    files: dict[str, str] = {}
    for path in merge_file_paths(manifest):
        file_path = root / path
        if file_path.is_file():
            files[path] = file_path.read_text(encoding="utf-8")
    return {"manifest": manifest, "files": files}


async def fetch_bundle(
    owner: str,
    name: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    url = f"{CLAWSOULS_API_BASE}/bundle/{owner}/{name}"
    if client is None:
        async with httpx.AsyncClient(timeout=30.0) as session:
            response = await session.get(url)
    else:
        response = await client.get(url)
    if response.status_code == 404:
        raise ValueError(f"ClawSouls soul not found: {owner}/{name}")
    if response.status_code >= 400:
        raise ValueError(
            f"ClawSouls API error {response.status_code}: {response.text[:200]}"
        )
    data = response.json()
    if not isinstance(data, dict) or "manifest" not in data:
        raise ValueError("Invalid ClawSouls bundle response")
    return data


def convert_bundle(
    bundle: dict[str, Any],
    *,
    msv_preset: str | None = None,
    owner: str | None = None,
    name: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    manifest = dict(bundle.get("manifest") or {})
    files = dict(bundle.get("files") or {})
    warnings: list[str] = []

    license_id = str(manifest.get("license") or "").strip()
    if license_id and license_id not in ALLOWED_LICENSES:
        raise ValueError(
            f"License {license_id} is not in SoulOS auto-import allowlist"
        )

    environment = str(manifest.get("environment") or "virtual").lower()
    if environment in ("embodied", "hybrid"):
        warnings.append(
            f"ClawSouls soul declares environment={environment}; "
            "physical fields are ignored in SoulOS text runtime"
        )

    description = merge_markdown(manifest, files)
    display = strip_emoji(
        str(manifest.get("displayName") or manifest.get("name") or "Assistant")
    )
    soul_name = display or str(manifest.get("name") or "Assistant")
    category = manifest.get("category")
    tags = manifest.get("tags") if isinstance(manifest.get("tags"), list) else []
    role = category_to_role(
        str(category) if category else None,
        [str(t) for t in tags],
    )

    preset_name = resolve_preset_name(manifest, msv_preset)
    preset = preset_bundle(preset_name)
    if preset_name != "default" or msv_preset:
        warnings.append(f"MSV preset applied: {preset_name}")
    elif resolve_preset_name(manifest) == "default":
        warnings.append(
            "MSV preset applied: default (no curated preset for this soul name)"
        )

    inner_default = str(
        (manifest.get("disclosure") or {}).get("summary")
        or manifest.get("description")
        or preset.get("baseline_msv", {}).get("inner_monologue", "")
    ).strip()
    baseline_msv = copy.deepcopy(preset["baseline_msv"])
    if inner_default:
        baseline_msv["inner_monologue"] = inner_default[:500]

    soul_payload: dict[str, Any] = {
        "name": soul_name,
        "role": role,
        "description": description,
        "attachment_style": preset.get("attachment_style", "Secure"),
        "baseline_msv": baseline_msv,
    }
    if tags:
        soul_payload["capabilities"] = [str(t) for t in tags[:10]]

    version = str(manifest.get("version") or "").strip()
    ref_owner = owner or "clawsouls"
    ref_name = name or str(manifest.get("name") or "")
    author = manifest_author(manifest)
    attribution_url = clawsouls_soul_url(ref_owner, ref_name)
    runtime_config: dict[str, Any] = {
        "source": {
            "type": "clawsouls",
            "owner": ref_owner,
            "name": ref_name,
            "version": version or None,
            "ref": f"{ref_owner}/{ref_name}" + (f"@{version}" if version else ""),
            "spec_version": manifest.get("specVersion"),
            "license": license_id or None,
            "author": author,
            "url": attribution_url,
            "attribution_notice": (
                f"Persona content from ClawSouls ({ref_owner}/{ref_name}), "
                f"license {license_id or 'see registry'}. "
                "Converted by SoulOS: merged Soul Spec markdown; added HEXACO MSV."
            ),
        },
        "clawsouls": {
            "msv_preset": preset_name,
            "warnings": list(warnings),
        },
    }
    if license_id == "Apache-2.0":
        warnings.append(
            "Apache-2.0 soul: retain attribution and license if you redistribute converted files"
        )
    if isinstance(manifest.get("allowedTools"), list):
        runtime_config["clawsouls"]["allowed_tools"] = manifest["allowedTools"]

    validate_soul_payload(soul_payload)
    return soul_payload, runtime_config, warnings


async def import_clawsouls_soul(
    owner: str,
    name: str,
    *,
    version: str | None = None,
    msv_preset: str | None = None,
    local_dir: Path | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    if local_dir is not None:
        bundle = load_local_bundle(local_dir)
    else:
        bundle = await fetch_bundle(owner, name, client=client)
    soul, runtime_config, warnings = convert_bundle(
        bundle,
        msv_preset=msv_preset,
        owner=owner,
        name=name,
    )
    if version:
        runtime_config["source"]["version"] = version
    return soul, runtime_config, warnings
