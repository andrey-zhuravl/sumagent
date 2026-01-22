from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class IndexEntry:
    file_hash_sha256: str
    summary_path: str
    size_bytes: int
    mtime: float


@dataclass
class DirIndexEntry:
    dir_hash_sha256: str
    summary_path: str
    mtime: float


@dataclass
class IndexData:
    schema: str
    repo_root: str
    created_at: str
    updated_at: str
    files: dict[str, IndexEntry]
    dirs: dict[str, DirIndexEntry]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "repo_root": self.repo_root,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": {
                path: {
                    "file_hash_sha256": entry.file_hash_sha256,
                    "summary_path": entry.summary_path,
                    "size_bytes": entry.size_bytes,
                    "mtime": entry.mtime,
                }
                for path, entry in self.files.items()
            },
            "dirs": {
                path: {
                    "dir_hash_sha256": entry.dir_hash_sha256,
                    "summary_path": entry.summary_path,
                    "mtime": entry.mtime,
                }
                for path, entry in self.dirs.items()
            },
        }


DEFAULT_SCHEMA = "Index.v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_index(path: Path) -> IndexData | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    files = {
        rel: IndexEntry(
            file_hash_sha256=entry["file_hash_sha256"],
            summary_path=entry["summary_path"],
            size_bytes=entry["size_bytes"],
            mtime=entry["mtime"],
        )
        for rel, entry in data.get("files", {}).items()
    }
    dirs = {
        rel: DirIndexEntry(
            dir_hash_sha256=entry["dir_hash_sha256"],
            summary_path=entry["summary_path"],
            mtime=entry["mtime"],
        )
        for rel, entry in data.get("dirs", {}).items()
    }
    return IndexData(
        schema=data.get("schema", DEFAULT_SCHEMA),
        repo_root=data.get("repo_root", ""),
        created_at=data.get("created_at", utc_now_iso()),
        updated_at=data.get("updated_at", utc_now_iso()),
        files=files,
        dirs=dirs,
    )


def new_index(repo_root: Path) -> IndexData:
    now = utc_now_iso()
    return IndexData(
        schema=DEFAULT_SCHEMA,
        repo_root=str(repo_root),
        created_at=now,
        updated_at=now,
        files={},
        dirs={},
    )


def save_index(path: Path, index: IndexData) -> None:
    index.updated_at = utc_now_iso()
    path.write_text(json.dumps(index.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
