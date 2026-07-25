"""First-party MIT SoulPacks — load, compile, list, export.

Layout policy (v1): each pack id is a **single unversioned directory** under
SOULPACKS_ROOT (e.g. ``support-agent/``). The ``version`` field in pack.json is
metadata for ``external_key`` only — side-by-side ``@1.0.0`` / ``@2.0.0`` trees
are not supported. Bump version in place or replace the pack directory.

MSV resolution precedence (highest wins):

1. Explicit ``baseline_msv`` in pack.json
2. Named preset: request ``msv_preset`` or manifest ``msv_preset`` → ``_presets.yaml``
3. ``default_msv_dict()`` from soul_validation (schema defaults — not a zero vector)
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml

from soul_validation import default_msv_dict, validate_soul_payload

ALLOWED_LICENSE = "MIT"
# Pack ids / catalog paths: single path segment only (no slashes or ..)
_SAFE_SEGMENT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


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


def _safe_segment(value: str, *, label: str) -> str:
    text = (value or "").strip()
    if not text or not _SAFE_SEGMENT.match(text):
        raise SoulPackError(f"Invalid {label}: {value!r}")
    if text in (".", "..") or "/" in text or "\\" in text:
        raise SoulPackError(f"Invalid {label}: {value!r}")
    return text


def _ensure_under(root: Path, path: Path, *, label: str) -> Path:
    """Resolve path and require it stays inside root (no symlink escape)."""
    root_res = root.resolve()
    try:
        resolved = path.resolve(strict=False)
    except OSError as e:
        raise SoulPackError(f"{label}: cannot resolve path") from e
    try:
        resolved.relative_to(root_res)
    except ValueError as e:
        raise SoulPackError(
            f"{label}: path escapes SoulPacks root ({root_res})"
        ) from e
    return resolved


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
    root = (root or packs_root()).resolve()
    safe_id = _safe_segment(pack_id, label="pack_id")
    pack_dir = root / safe_id
    manifest_path = pack_dir / "pack.json"
    if not manifest_path.is_file():
        for entry in _read_catalog(root):
            if entry.get("id") == safe_id:
                rel = _safe_segment(str(entry.get("path") or safe_id), label="catalog path")
                pack_dir = root / rel
                manifest_path = pack_dir / "pack.json"
                break
    pack_dir = _ensure_under(root, pack_dir, label="pack directory")
    manifest_path = _ensure_under(root, manifest_path, label="pack.json")
    if not manifest_path.is_file():
        raise SoulPackNotFoundError(f"SoulPack not found: {pack_id}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise SoulPackError(f"Invalid pack.json for {pack_id}")
    return pack_dir, manifest


def _merge_markdown(root: Path, pack_dir: Path, files: list[str]) -> str:
    """Merge markdown files; every path must resolve under pack_dir (⊆ root)."""
    pack_dir = _ensure_under(root, pack_dir, label="pack directory")
    parts: list[str] = []
    for rel in files:
        rel_text = str(rel).strip()
        if not rel_text or rel_text.startswith("/") or rel_text.startswith("\\"):
            raise SoulPackError(f"Invalid pack file path: {rel!r}")
        # Reject empty segments / parent refs before join
        for segment in Path(rel_text).parts:
            if segment in ("", ".", ".."):
                raise SoulPackError(f"Invalid pack file path: {rel!r}")
        candidate = pack_dir / rel_text
        path = _ensure_under(pack_dir, candidate, label=f"pack file {rel!r}")
        # Also require under SOULPACKS_ROOT (defense in depth)
        _ensure_under(root, path, label=f"pack file {rel!r}")
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
    """Precedence: explicit baseline_msv >> msv_preset lookup >> default_msv_dict()."""
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
    root = (root or packs_root()).resolve()
    pack_dir, manifest = load_pack(pack_id, root=root)

    license_id = str(manifest.get("license") or "").strip()
    if license_id != ALLOWED_LICENSE:
        raise SoulPackLicenseError(
            f"License {license_id or '(missing)'} is not MIT; SoulPacks require MIT"
        )

    files = manifest.get("files") or ["SOUL.md"]
    if not isinstance(files, list) or not files:
        raise SoulPackError("pack.json 'files' must be a non-empty list")

    description = _merge_markdown(root, pack_dir, [str(f) for f in files])
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


def _atomic_write_text(path: Path, content: str) -> None:
    """Write via temp file + os.replace to avoid torn reads across workers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def export_pack(soul: dict[str, Any], out_dir: Path | str) -> Path:
    """Write a MIT SoulPack directory from a validated soul dict (atomic files)."""
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
    _atomic_write_text(out / "pack.json", json.dumps(pack_json, indent=2) + "\n")
    _atomic_write_text(out / "SOUL.md", payload["description"].strip() + "\n")
    return out
