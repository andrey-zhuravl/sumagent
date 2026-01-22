from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sumagent_a.index import IndexData, load_index


@dataclass
class StageAData:
    index: IndexData
    file_summaries: dict[str, dict[str, Any]]
    dir_summaries: dict[str, dict[str, Any]]


def _load_summary(summary_dir: Path, summary_path: str) -> dict[str, Any]:
    path = summary_dir / summary_path
    return json.loads(path.read_text(encoding="utf-8"))


def load_stage_a(summary_dir: Path) -> StageAData:
    index_path = summary_dir / "index.json"
    index = load_index(index_path)
    if index is None:
        raise FileNotFoundError(f"Stage A index not found at {index_path}")
    file_summaries = {
        rel: _load_summary(summary_dir, entry.summary_path) for rel, entry in index.files.items()
    }
    dir_summaries = {
        rel: _load_summary(summary_dir, entry.summary_path) for rel, entry in index.dirs.items()
    }
    return StageAData(index=index, file_summaries=file_summaries, dir_summaries=dir_summaries)
