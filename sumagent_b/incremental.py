from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class ModulePlan:
    module_id: str
    module_input_hash: str
    dirty: bool


@dataclass
class ViewPlan:
    aspect_id: str
    aspect_input_hash: str
    dirty: bool


def hash_items(items: list[str]) -> str:
    digest = hashlib.sha256()
    for item in sorted(items):
        digest.update(item.encode("utf-8"))
    return digest.hexdigest()


def compute_module_input_hash(module_files: list[dict[str, Any]]) -> str:
    hashes = [f"{file_summary['relative_path']}:{file_summary['file_hash_sha256']}" for file_summary in module_files]
    return hash_items(hashes)


def compute_aspect_input_hash(selected_files: list[dict[str, Any]]) -> str:
    hashes = [f"{file_summary['relative_path']}:{file_summary['file_hash_sha256']}" for file_summary in selected_files]
    return hash_items(hashes)


def plan_modules(
    module_tree: dict[str, Any],
    file_summaries: dict[str, dict[str, Any]],
    previous: dict[str, dict[str, str]],
    *,
    force: bool = False,
) -> dict[str, ModulePlan]:
    plans: dict[str, ModulePlan] = {}
    for module in module_tree["modules"]:
        module_id = module["module_id"]
        root_path = module["root_path"]
        module_files = [
            summary
            for path, summary in file_summaries.items()
            if root_path == "." or path == root_path or path.startswith(f"{root_path}/")
        ]
        module_input_hash = compute_module_input_hash(module_files)
        previous_hash = previous.get(module_id, {}).get("module_input_hash")
        dirty = force or (module_input_hash != previous_hash)
        plans[module_id] = ModulePlan(module_id=module_id, module_input_hash=module_input_hash, dirty=dirty)
    return plans


def plan_views(
    aspects: list[dict[str, str]],
    selected_by_aspect: dict[str, list[dict[str, Any]]],
    previous: dict[str, dict[str, str]],
    *,
    force: bool = False,
) -> dict[str, ViewPlan]:
    plans: dict[str, ViewPlan] = {}
    for aspect in aspects:
        aspect_id = aspect["id"]
        selected = selected_by_aspect.get(aspect_id, [])
        aspect_input_hash = compute_aspect_input_hash(selected)
        previous_hash = previous.get(aspect_id, {}).get("aspect_input_hash")
        dirty = force or (aspect_input_hash != previous_hash)
        plans[aspect_id] = ViewPlan(aspect_id=aspect_id, aspect_input_hash=aspect_input_hash, dirty=dirty)
    return plans
