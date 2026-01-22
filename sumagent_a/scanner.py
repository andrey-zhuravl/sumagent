from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path


@dataclass(frozen=True)
class FileInfo:
    relative_path: str
    abs_path: Path
    size_bytes: int
    mtime: float
    ext: str


@dataclass(frozen=True)
class DirInfo:
    relative_path: str
    abs_path: Path
    mtime: float


def should_exclude_file(relative_path: str, file_globs: list[str]) -> bool:
    return any(fnmatch(relative_path, pattern) or fnmatch(Path(relative_path).name, pattern) for pattern in file_globs)


def scan_repo(
    repo_root: Path,
    *,
    dir_exclusions: list[str],
    file_globs: list[str],
) -> tuple[list[FileInfo], list[DirInfo]]:
    files: list[FileInfo] = []
    dirs: list[DirInfo] = []

    for current_root, dirnames, filenames in repo_root.walk():
        rel_dir = Path(current_root).relative_to(repo_root)
        rel_dir_str = "." if rel_dir == Path(".") else rel_dir.as_posix()

        if rel_dir_str != "." and rel_dir.parts:
            if any(part in dir_exclusions for part in rel_dir.parts):
                dirnames[:] = []
                continue

        dirnames[:] = [d for d in dirnames if d not in dir_exclusions]
        stat = Path(current_root).stat()
        dirs.append(DirInfo(relative_path=rel_dir_str, abs_path=Path(current_root), mtime=stat.st_mtime))

        for filename in filenames:
            relative_path = (rel_dir / filename).as_posix() if rel_dir_str != "." else filename
            if should_exclude_file(relative_path, file_globs):
                continue
            abs_path = Path(current_root) / filename
            file_stat = abs_path.stat()
            files.append(
                FileInfo(
                    relative_path=relative_path,
                    abs_path=abs_path,
                    size_bytes=file_stat.st_size,
                    mtime=file_stat.st_mtime,
                    ext=abs_path.suffix.lower(),
                )
            )

    return files, dirs
