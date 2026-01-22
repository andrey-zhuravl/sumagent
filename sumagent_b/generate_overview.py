from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm_client import LLMClient
from .render import render_project_overview


def generate_project_overview(
    *,
    module_tree: dict[str, Any],
    module_results: dict[str, Any],
    file_summaries: dict[str, dict[str, Any]],
    out_dir: Path,
    llm_client: LLMClient | None,
    dry_run: bool,
) -> Path:
    overview_path = out_dir / "project_overview.md"
    important_files = sorted(file_summaries.keys())[:10]
    if dry_run:
        content = ""
    elif llm_client:
        prompt = "Project overview summary"
        content = llm_client.summarize(prompt)
    else:
        content = render_project_overview(module_tree, {}, important_files)
    if "Most important files" not in content:
        content = f"{content}\n\n## Most important files\n" + "\n".join(f"- {path}" for path in important_files)
    if "key_files" not in content:
        content = f"{content}\n\n## key_files\n" + "\n".join(f"- {path}" for path in important_files)
    if not dry_run:
        overview_path.write_text(content, encoding="utf-8")
    return overview_path
