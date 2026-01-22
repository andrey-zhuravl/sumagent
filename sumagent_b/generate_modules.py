from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm_client import LLMClient
from .logging import RunLogger
from .render import render_module_summary


@dataclass
class ModuleResult:
    module_id: str
    path: Path
    key_files: list[str]


def generate_modules(
    *,
    module_tree: dict[str, Any],
    file_summaries: dict[str, dict[str, Any]],
    module_plans: dict[str, Any],
    out_dir: Path,
    llm_client: LLMClient | None,
    run_logger: RunLogger,
    dry_run: bool,
) -> dict[str, ModuleResult]:
    results: dict[str, ModuleResult] = {}
    modules_dir = out_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    for module in module_tree["modules"]:
        module_id = module["module_id"]
        plan = module_plans.get(module_id)
        if plan is None or not plan.dirty:
            continue
        root_path = module["root_path"]
        key_files = sorted(
            [
                path
                for path in file_summaries.keys()
                if root_path == "." or path == root_path or path.startswith(f"{root_path}/")
            ]
        )
        summaries = [file_summaries[path] for path in key_files]
        if dry_run:
            content = ""
        elif llm_client:
            prompt = f"Module {module['name']}\nFiles: {', '.join(key_files)}"
            content = llm_client.summarize(prompt)
            run_logger.metrics.llm_calls_count += 1
        else:
            content = render_module_summary(module["name"], summaries, key_files)
        if "key_files" not in content:
            content = f"{content}\n\n## key_files\n" + "\n".join(f"- {path}" for path in key_files)
        path = modules_dir / f"{module_id}.md"
        if not dry_run:
            path.write_text(content, encoding="utf-8")
        results[module_id] = ModuleResult(module_id=module_id, path=path, key_files=key_files)
        run_logger.metrics.modules_built += 1
    return results
