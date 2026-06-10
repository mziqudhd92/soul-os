"""Bundle repo docs: compact agent context (default) or full markdown dump (--full)."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_COMPACT = ROOT / "docs" / "SOULOS_AGENT_CONTEXT.md"
OUT_FULL = ROOT / "docs" / "SOULOS_AGENT_CONTEXT_FULL.md"

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".cursor",
}

EXTRA_JSON = [
    ROOT / "spec/soul.schema.json",
    ROOT / "examples/mcp/cursor-mcp.json",
]

PRIORITY_PREFIXES = [
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/",
    "packages/",
    "examples/",
    ".github/",
    "AGENTS.md",
    "CLAUDE.md",
]


def rel_label(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sort_key(path: Path) -> tuple[int, str]:
    label = rel_label(path)
    for i, prefix in enumerate(PRIORITY_PREFIXES):
        if label == prefix or label.startswith(prefix):
            return (i, label)
    return (len(PRIORITY_PREFIXES), label)


def discover_markdown(exclude: Path) -> list[Path]:
    found: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.resolve() == exclude.resolve():
            continue
        if path.name == "SOULOS_AGENT_CONTEXT_FULL.md":
            continue
        found.append(path)
    return sorted(found, key=sort_key)


def discover_full_sections() -> list[tuple[str, Path]]:
    sections: list[tuple[str, Path]] = [
        (rel_label(p), p) for p in discover_markdown(OUT_FULL)
    ]
    for path in EXTRA_JSON:
        if path.is_file():
            sections.append((rel_label(path), path))
    return sections


FULL_HEADER = """# SoulOS — Complete Documentation (full dump)

> All repo markdown + `spec/soul.schema.json` + `examples/mcp/cursor-mcp.json`.
> **Upload to agents:** use the shorter `docs/SOULOS_AGENT_CONTEXT.md` instead.
> **Regenerate:** `python3 scripts/doc-gen/bundle_agent_context.py --full`
> **Generated:** {generated} · **{count} sections**

## Bundled sources

{toc}

---
"""


def section_block(label: str, path: Path, body: str) -> str:
    if path.suffix == ".json":
        inner = f"```json\n{body.rstrip()}\n```"
    else:
        inner = body.rstrip()
    return f"\n## Source: `{label}`\n\n{inner}\n"


def write_full() -> None:
    sections = discover_full_sections()
    toc_lines = [f"- `{label}`" for label, _ in sections]
    parts = [
        FULL_HEADER.format(
            generated=date.today().isoformat(),
            count=len(sections),
            toc="\n".join(toc_lines),
        )
    ]
    for label, path in sections:
        parts.append(section_block(label, path, path.read_text(encoding="utf-8")))
    OUT_FULL.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FULL.relative_to(ROOT)} — {len(sections)} sections, {OUT_FULL.stat().st_size:,} bytes")


def write_compact() -> None:
    if not OUT_COMPACT.is_file():
        raise SystemExit(
            f"Compact file missing: {OUT_COMPACT}. Restore docs/SOULOS_AGENT_CONTEXT.md in repo."
        )
    size = OUT_COMPACT.stat().st_size
    print(f"Compact agent context: {OUT_COMPACT.relative_to(ROOT)} ({size:,} bytes) — edit file directly")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle SoulOS docs for AI agents")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate full markdown dump to docs/SOULOS_AGENT_CONTEXT_FULL.md",
    )
    args = parser.parse_args()
    if args.full:
        write_full()
    else:
        write_compact()


if __name__ == "__main__":
    main()
