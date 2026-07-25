"""First-party MIT SoulPacks — load, compile, list, export."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from soul_validation import default_msv_dict, validate_soul_payload

ALLOWED_LICENSE = "MIT"


class SoulPackError(ValueError):
    """Base SoulPack error."""

    code = "SOULPACK_INVALID"


class SoulPackNotFoundError(SoulPackError):
    code = "SOULPACK_NOT_FOUND"


class SoulPackLicenseError(SoulPackError):
    code = "SOULPACK_LICENSE_REJECTED"


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for ancestor in [here, *here.parents]:
        candidate = ancestor / "packs" / "soulpacks"
        if candidate.is_dir():
            return ancestor
        if (ancestor / "spec" / "soul.schema.json").is_file() and (
            ancestor / "packs"
        ).exists():
            return ancestor
    return here.parents[3]


def packs_root() -> Path:
    override = os.getenv("SOULPACKS_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (_repo_root() / "packs" / "soulpacks").resolve()


def default_external_key(pack_id: str, version: str) -> str:
    return f"soulos:{pack_id}@{version}"


def _load_presets(root: Path) -> dict[str, Any]:
    path = root / "_presets.yaml"
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data.get("presets") or data


def _read_catalog(root: Path) -> list[dict[str, Any]]:
    catalog_path = root / "catalog.json"
    if not catalog_path.is_file():
        return []
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    packs = data.get("packs") if isinstance(data, dict) else data
    if not isinstance(packs, list):
        return []
    return [p for p in packs if isinstance(p, dict)]


def list_packs(*, q: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    root = root or packs_root()
    packs = _read_catalog(root)
    # Ensure on-disk packs appear even if catalog is thin
    if not packs and root.is_dir():
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "pack.json").is_file():
                manifest = json.loads((child / "pack.json").read_text(encoding="utf-8"))
                packs.append(
                    {
                        "id": manifest.get("id", child.name),
                        "name": manifest.get("name", child.name),
                        "version": manifest.get("version", "0.0.0"),
                        "tags": manifest.get("tags") or [],
                        "license": manifest.get("license", ALLOWED_LICENSE),
                        "path": child.name,
                    }
                )
    if q:
        needle = q.strip().lower()
        packs = [
            p
            for p in packs
            if needle in str(p.get("id", "")).lower()
            or needle in str(p.get("name", "")).lower()
            or any(needle in str(t).lower() for t in (p.get("tags") or []))
        ]
    return packs


def load_pack(pack_id: str, *, root: Path | None = None) -> tuple[Path, dict[str, Any]]:
    root = root or packs_root()
    pack_dir = root / pack_id
    manifest_path = pack_dir / "pack.json"
    if not manifest_path.is_file():
        # catalog may remap path
        for entry in _read_catalog(root):
            if entry.get("id") == pack_id:
                rel = entry.get("path") or pack_id
                pack_dir = root / rel
                manifest_path = pack_dir / "pack.json"
                break
    if not manifest_path.is_file():
        raise SoulPackNotFoundError(f"SoulPack not found: {pack_id}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise SoulPackError(f"Invalid pack.json for {pack_id}")
    return pack_dir, manifest


def _merge_markdown(pack_dir: Path, files: list[str]) -> str:
    parts: list[str] = []
    for rel in files:
        path = pack_dir / rel
        if not path.is_file():
            raise SoulPackError(f"Missing pack file: {rel}")
        text = path.read_text(encoding="utf-8").strip()
        if text:
            parts.append(text)
    if not parts:
        raise SoulPackError("SoulPack has no markdown content")
    return "\n\n".join(parts)


def _resolve_msv(
    manifest: dict[str, Any],
    presets: dict[str, Any],
    *,
    msv_preset: str | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if isinstance(manifest.get("baseline_msv"), dict):
        return dict(manifest["baseline_msv"]), warnings

    preset_name = msv_preset or manifest.get("msv_preset")
    if preset_name and preset_name in presets:
        base = default_msv_dict()
        preset = presets[preset_name]
        if isinstance(preset, dict):
            for key in ("hexaco", "moral_foundations", "drives"):
                if isinstance(preset.get(key), dict):
                    base[key] = {**base[key], **preset[key]}
            for key in ("epistemic_uncertainty", "inner_monologue"):
                if key in preset:
                    base[key] = preset[key]
        warnings.append(f"Applied MSV preset '{preset_name}'")
        return base, warnings

    warnings.append("No baseline_msv or preset; using default MSV")
    return default_msv_dict(), warnings


def compile_pack(
    pack_id: str,
    *,
    root: Path | None = None,
    msv_preset: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Return (soul, runtime_config, warnings)."""
    root = root or packs_root()
    pack_dir, manifest = load_pack(pack_id, root=root)

    license_id = str(manifest.get("license") or "").strip()
    if license_id != ALLOWED_LICENSE:
        raise SoulPackLicenseError(
            f"License {license_id or '(missing)'} is not MIT; SoulPacks require MIT"
        )

    files = manifest.get("files") or ["SOUL.md"]
    if not isinstance(files, list) or not files:
        raise SoulPackError("pack.json 'files' must be a non-empty list")

    description = _merge_markdown(pack_dir, [str(f) for f in files])
    presets = _load_presets(root)
    baseline_msv, warnings = _resolve_msv(manifest, presets, msv_preset=msv_preset)

    soul: dict[str, Any] = {
        "name": str(manifest.get("name") or pack_id),
        "role": str(manifest.get("role") or "Agent"),
        "description": description,
        "attachment_style": str(manifest.get("attachment_style") or "Secure"),
        "baseline_msv": baseline_msv,
    }
    if manifest.get("capabilities"):
        soul["capabilities"] = list(manifest["capabilities"])
    if manifest.get("status"):
        soul["status"] = manifest["status"]

    try:
        validate_soul_payload(soul)
    except ValueError as e:
        raise SoulPackError(str(e)) from e

    version = str(manifest.get("version") or "0.0.0")
    runtime_config = {
        "source": {
            "type": "soulpack",
            "id": str(manifest.get("id") or pack_id),
            "version": version,
            "license": ALLOWED_LICENSE,
        }
    }
    return soul, runtime_config, warnings


def export_pack(soul: dict[str, Any], out_dir: Path | str) -> Path:
    """Write a MIT SoulPack directory from a validated soul dict."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    validated = validate_soul_payload(soul)
    payload = validated.model_dump()
    pack_id = re.sub(r"[^a-z0-9-]+", "-", payload["name"].lower()).strip("-") or "soul"
    pack_json = {
        "id": pack_id,
        "name": payload["name"],
        "version": "1.0.0",
        "license": ALLOWED_LICENSE,
        "role": payload["role"],
        "attachment_style": payload["attachment_style"],
        "files": ["SOUL.md"],
        "baseline_msv": payload["baseline_msv"],
        "status": payload.get("status") or "available",
    }
    if payload.get("capabilities"):
        pack_json["capabilities"] = payload["capabilities"]
    (out / "pack.json").write_text(
        json.dumps(pack_json, indent=2) + "\n", encoding="utf-8"
    )
    (out / "SOUL.md").write_text(payload["description"].strip() + "\n", encoding="utf-8")
    return out
