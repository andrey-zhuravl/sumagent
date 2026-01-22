from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def summary_filename(relative_path: str) -> str:
    return f"{sha256_text(relative_path)}.json"


def resolve_out_dir(repo_root: Path, out_dir: str) -> Path:
    out_path = Path(out_dir)
    if out_path.is_absolute():
        return out_path
    return (repo_root / out_path).resolve()


def ensure_within_repo(repo_root: Path, path: Path) -> None:
    repo_root_resolved = repo_root.resolve()
    path_resolved = path.resolve()
    if repo_root_resolved not in path_resolved.parents and repo_root_resolved != path_resolved:
        raise ValueError(f"Path {path_resolved} is outside repo root {repo_root_resolved}")
