"""SoulOS product version — single source of truth helpers.

Canonical file: repo-root ``VERSION`` (one line, semver, no ``v`` prefix).

All package manifests, docs indexes, schema.org, Helm ``appVersion``, and the
site footer must match this file. Use ``npm run version:sync`` after bumping
``VERSION``, then ``npm run version:check`` / ``npm run doc:check``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_version(root: Path | None = None) -> str:
    """Return the product version from ``VERSION``."""
    base = Path(root) if root is not None else ROOT
    path = base / "VERSION"
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty version file: {path}")
    line = text.splitlines()[0].strip()
    if line.startswith("#"):
        raise ValueError(f"VERSION must start with semver, got comment: {line!r}")
    if line.startswith("v"):
        line = line[1:]
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", line):
        raise ValueError(f"Invalid semver in {path}: {line!r}")
    return line


def _replace_toml_version(text: str, version: str) -> str:
    return re.sub(
        r'(?m)^(version\s*=\s*")[^"]*(")',
        rf"\g<1>{version}\2",
        text,
        count=1,
    )


def sync_version(root: Path | None = None, *, write: bool = True) -> list[str]:
    """Propagate VERSION into all product version mirrors. Returns changed paths."""
    base = Path(root) if root is not None else ROOT
    version = read_version(base)
    changed: list[str] = []

    def write_if_changed(path: Path, new_text: str) -> None:
        old = path.read_text(encoding="utf-8") if path.is_file() else None
        if old == new_text:
            return
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_text, encoding="utf-8")
        changed.append(str(path.relative_to(base)))

    pkg_path = base / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    if pkg.get("version") != version:
        pkg["version"] = version
        write_if_changed(pkg_path, json.dumps(pkg, indent=2) + "\n")

    lock_path = base / "package-lock.json"
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        dirty = False
        if lock.get("version") != version:
            lock["version"] = version
            dirty = True
        packages = lock.get("packages")
        if isinstance(packages, dict) and "" in packages:
            if packages[""].get("version") != version:
                packages[""]["version"] = version
                dirty = True
        if dirty:
            write_if_changed(lock_path, json.dumps(lock, indent=2) + "\n")

    schema_path = base / "schema" / "project.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema.get("version") != version:
        schema["version"] = version
        write_if_changed(schema_path, json.dumps(schema, indent=2, ensure_ascii=False) + "\n")

    for rel in (
        "packages/soulos-core/pyproject.toml",
        "packages/soulos-sdk/python/pyproject.toml",
        "packages/soulos-gateway/pyproject.toml",
        "packages/soulos-studio/pyproject.toml",
        "packages/soulos-inference-bridge/pyproject.toml",
    ):
        path = base / rel
        text = path.read_text(encoding="utf-8")
        new_text = _replace_toml_version(text, version)
        if new_text != text:
            write_if_changed(path, new_text)

    ts_sdk = base / "packages" / "soulos-sdk" / "ts" / "package.json"
    ts_data = json.loads(ts_sdk.read_text(encoding="utf-8"))
    if ts_data.get("version") != version:
        ts_data["version"] = version
        write_if_changed(ts_sdk, json.dumps(ts_data, indent=2) + "\n")

    chart = base / "deploy" / "helm" / "soulos" / "Chart.yaml"
    if chart.is_file():
        text = chart.read_text(encoding="utf-8")
        new_text = re.sub(
            r'(?m)^(appVersion:\s*")[^"]*(")',
            rf"\g<1>{version}\2",
            text,
            count=1,
        )
        if new_text != text:
            write_if_changed(chart, new_text)

    for name, pattern in (
        ("llms.txt", r"(License: MIT · Version:\s*)\S+"),
        ("llms-full.txt", r"(\*\*License:\*\* MIT · Version\s+)\S+"),
    ):
        path = base / name
        text = path.read_text(encoding="utf-8")
        new_text, n = re.subn(pattern, rf"\g<1>{version}", text, count=1)
        if n and new_text != text:
            write_if_changed(path, new_text)

    example = base / "examples" / "fastapi-hybrid" / "app.py"
    if example.is_file():
        text = example.read_text(encoding="utf-8")
        new_text = re.sub(
            r'(version=")[^"]*(")',
            rf'\g<1>{version}\2',
            text,
            count=1,
        )
        if new_text != text:
            write_if_changed(example, new_text)

    return changed


def collect_mismatches(root: Path | None = None) -> list[str]:
    """Return human-readable mismatch strings (empty if in sync)."""
    base = Path(root) if root is not None else ROOT
    version = read_version(base)
    errors: list[str] = []

    def expect(label: str, got: str | None) -> None:
        if got != version:
            errors.append(f"{label}: expected {version!r}, got {got!r}")

    pkg = json.loads((base / "package.json").read_text(encoding="utf-8"))
    expect("package.json", str(pkg.get("version", "")))

    schema = json.loads((base / "schema" / "project.json").read_text(encoding="utf-8"))
    expect("schema/project.json", str(schema.get("version", "")))

    for rel in (
        "packages/soulos-core/pyproject.toml",
        "packages/soulos-sdk/python/pyproject.toml",
        "packages/soulos-gateway/pyproject.toml",
        "packages/soulos-studio/pyproject.toml",
        "packages/soulos-inference-bridge/pyproject.toml",
    ):
        text = (base / rel).read_text(encoding="utf-8")
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
        expect(rel, m.group(1) if m else None)

    ts = json.loads(
        (base / "packages" / "soulos-sdk" / "ts" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    expect("packages/soulos-sdk/ts/package.json", str(ts.get("version", "")))

    chart = base / "deploy" / "helm" / "soulos" / "Chart.yaml"
    if chart.is_file():
        m = re.search(
            r'(?m)^appVersion:\s*"([^"]+)"', chart.read_text(encoding="utf-8")
        )
        expect("deploy/helm/soulos/Chart.yaml appVersion", m.group(1) if m else None)

    llms = (base / "llms.txt").read_text(encoding="utf-8")
    m = re.search(r"License: MIT · Version:\s*(\S+)", llms)
    expect("llms.txt", m.group(1) if m else None)

    llms_full = (base / "llms-full.txt").read_text(encoding="utf-8")
    m = re.search(r"\*\*License:\*\* MIT · Version\s+(\S+)", llms_full)
    expect("llms-full.txt", m.group(1) if m else None)

    changelog = (base / "CHANGELOG.md").read_text(encoding="utf-8")
    if version not in changelog:
        errors.append(f"CHANGELOG.md: missing version {version!r}")

    openapi = base / "docs" / "reference" / "openapi.kernel.json"
    if openapi.is_file():
        data = json.loads(openapi.read_text(encoding="utf-8"))
        info_ver = (data.get("info") or {}).get("version")
        expect("docs/reference/openapi.kernel.json info.version", str(info_ver or ""))

    return errors
