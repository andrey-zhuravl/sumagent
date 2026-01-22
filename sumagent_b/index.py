from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class StageBIndex:
    schema: str
    created_at: str
    updated_at: str
    modules: dict[str, dict[str, str]]
    views: dict[str, dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "modules": self.modules,
            "views": self.views,
        }


DEFAULT_SCHEMA = "StageBIndex.v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_stage_b_index(path: Path) -> StageBIndex | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return StageBIndex(
        schema=data.get("schema", DEFAULT_SCHEMA),
        created_at=data.get("created_at", utc_now_iso()),
        updated_at=data.get("updated_at", utc_now_iso()),
        modules=data.get("modules", {}),
        views=data.get("views", {}),
    )


def new_stage_b_index() -> StageBIndex:
    now = utc_now_iso()
    return StageBIndex(
        schema=DEFAULT_SCHEMA,
        created_at=now,
        updated_at=now,
        modules={},
        views={},
    )


def save_stage_b_index(path: Path, index: StageBIndex) -> None:
    index.updated_at = utc_now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
