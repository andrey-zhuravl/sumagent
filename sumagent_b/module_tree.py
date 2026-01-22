from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable


MODULE_ROOT_CANDIDATES = ["src", "app", "services", "packages", "modules", "server", "client"]


@dataclass(frozen=True)
class ModuleNode:
    module_id: str
    name: str
    root_path: str
    parent_module_id: str | None
    depth: int
    file_count: int
    labels: list[str]


@dataclass(frozen=True)
class ModuleEdge:
    from_module_id: str
    to_module_id: str
    kind: str = "contains"


def normalize_rel_path(path: str) -> str:
    if path in ("", "."):
        return "."
    return str(PurePosixPath(path))


def module_id_for_path(root_path: str) -> str:
    normalized = normalize_rel_path(root_path)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _gather_dirs(file_paths: Iterable[str]) -> set[str]:
    dirs: set[str] = {"."}
    for file_path in file_paths:
        posix = PurePosixPath(file_path)
        for parent in posix.parents:
            if str(parent) == ".":
                dirs.add(".")
            else:
                dirs.add(str(parent))
    return dirs


def _select_module_roots(dirs: set[str], ignore_paths: set[str]) -> list[str]:
    candidates = [root for root in MODULE_ROOT_CANDIDATES if root in dirs and root not in ignore_paths]
    top_level = {
        path
        for path in dirs
        if path not in (".", "") and len(PurePosixPath(path).parts) == 1 and path not in ignore_paths
    }
    if candidates:
        extras = [path for path in sorted(top_level) if path not in candidates]
        return sorted(candidates) + extras
    if top_level:
        return sorted(top_level)
    return ["."]


def _is_ignored(path: str, ignore_paths: set[str]) -> bool:
    for ignore in ignore_paths:
        if ignore == ".":
            return True
        if path == ignore or path.startswith(f"{ignore}/"):
            return True
    return False


def build_module_tree(
    file_paths: Iterable[str],
    *,
    ignore_paths: Iterable[str] | None = None,
    label_paths: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    ignore_set = {normalize_rel_path(path) for path in (ignore_paths or [])}
    label_paths = {normalize_rel_path(path): labels for path, labels in (label_paths or {}).items()}
    file_paths_filtered = [
        normalize_rel_path(path) for path in file_paths if not _is_ignored(normalize_rel_path(path), ignore_set)
    ]
    dirs = _gather_dirs(file_paths_filtered)
    module_roots = _select_module_roots(dirs, ignore_set)

    module_dirs = set()
    for root in module_roots:
        for path in dirs:
            if root == ".":
                module_dirs.add(path)
            elif path == root or path.startswith(f"{root}/"):
                module_dirs.add(path)
    if "." in dirs and "." not in module_dirs:
        module_dirs.add(".")

    modules: list[ModuleNode] = []
    for path in sorted(module_dirs, key=lambda p: (len(PurePosixPath(p).parts), p)):
        normalized = normalize_rel_path(path)
        parent_path = str(PurePosixPath(normalized).parent)
        parent_id = None
        if normalized != "." and parent_path in module_dirs:
            parent_id = module_id_for_path(parent_path)
        depth = 0 if normalized == "." else len(PurePosixPath(normalized).parts)
        file_count = sum(
            1
            for file_path in file_paths_filtered
            if normalized == "." or file_path == normalized or file_path.startswith(f"{normalized}/")
        )
        labels = sorted({label for path_prefix, labels in label_paths.items() if normalized.startswith(path_prefix) for label in labels})
        modules.append(
            ModuleNode(
                module_id=module_id_for_path(normalized),
                name=PurePosixPath(normalized).name if normalized != "." else "root",
                root_path=normalized,
                parent_module_id=parent_id,
                depth=depth,
                file_count=file_count,
                labels=labels,
            )
        )

    edges = [
        ModuleEdge(from_module_id=module.module_id, to_module_id=module.parent_module_id)
        for module in modules
        if module.parent_module_id
    ]

    path_to_module: dict[str, str] = {}
    module_dir_set = {module.root_path for module in modules}
    for file_path in file_paths_filtered:
        parent = str(PurePosixPath(file_path).parent)
        while parent not in module_dir_set and parent not in (".", ""):
            parent = str(PurePosixPath(parent).parent)
        resolved = parent if parent in module_dir_set else "."
        path_to_module[file_path] = module_id_for_path(resolved)

    return {
        "schema": "ModuleTree.v1",
        "repo_root": "",
        "generated_at": "",
        "modules": [
            {
                "module_id": module.module_id,
                "name": module.name,
                "root_path": module.root_path,
                "parent_module_id": module.parent_module_id,
                "depth": module.depth,
                "file_count": module.file_count,
                "labels": module.labels,
            }
            for module in modules
        ],
        "edges": [
            {"from_module_id": edge.from_module_id, "to_module_id": edge.to_module_id, "kind": edge.kind}
            for edge in edges
        ],
        "path_to_module": path_to_module,
        "module_roots": module_roots,
    }


def modules_topological(module_tree: dict[str, Any]) -> list[dict[str, Any]]:
    modules = module_tree["modules"]
    return sorted(modules, key=lambda mod: (-mod["depth"], mod["root_path"]))
