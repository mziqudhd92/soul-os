"""Append-only `.soul-memory/` episodic ledger (Phase 3)."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from pathlib import Path
from typing import Any

from runtime.soulignore import validate_memory_content

EPISODES_DIR = "episodes"
INDEX_FILE = "index.json"


def memory_root(workspace_root: Path) -> Path:
    return workspace_root / ".soul-memory"


def episode_hash(summary: str) -> str:
    return hashlib.sha256(summary.encode("utf-8")).hexdigest()[:8]


def episode_filename(summary: str, day: date | None = None) -> str:
    day = day or date.today()
    return f"{day.isoformat()}_{episode_hash(summary)}.jsonl"


def load_index(root: Path) -> dict[str, Any]:
    index_path = root / INDEX_FILE
    if not index_path.is_file():
        return {"episodes": [], "updated_at": None}
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"episodes": [], "updated_at": None}
    data.setdefault("episodes", [])
    return data


def save_index(root: Path, index: dict[str, Any]) -> None:
    index["updated_at"] = int(time.time())
    index_path = root / INDEX_FILE
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def append_episode_line(
    workspace_root: Path,
    summary: str,
    episode_type: str = "interaction",
    extra: dict[str, Any] | None = None,
) -> Path:
    validate_memory_content(summary, workspace_root)
    root = memory_root(workspace_root)
    episodes_dir = root / EPISODES_DIR
    episodes_dir.mkdir(parents=True, exist_ok=True)

    content_hash = episode_hash(summary)
    line: dict[str, Any] = {
        "timestamp": int(time.time()),
        "type": episode_type,
        "hash": content_hash,
        "summary": summary.strip(),
    }
    if extra:
        line.update(extra)

    filename = episode_filename(summary)
    episode_path = episodes_dir / filename
    with episode_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    index = load_index(root)
    episodes = index.setdefault("episodes", [])
    if not any(e.get("file") == filename for e in episodes):
        episodes.append(
            {
                "file": filename,
                "hash": content_hash,
                "type": episode_type,
                "created_at": line["timestamp"],
            }
        )
    save_index(root, index)
    return episode_path


def iter_episode_lines(workspace_root: Path) -> list[dict[str, Any]]:
    root = memory_root(workspace_root)
    episodes_dir = root / EPISODES_DIR
    if not episodes_dir.is_dir():
        return []

    lines: list[dict[str, Any]] = []
    for path in sorted(episodes_dir.glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                row["_file"] = path.name
                lines.append(row)
    return lines


def export_memory_json(workspace_root: Path) -> dict[str, Any]:
    return {
        "index": load_index(memory_root(workspace_root)),
        "episodes": iter_episode_lines(workspace_root),
    }
