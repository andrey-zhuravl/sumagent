from __future__ import annotations

from typing import Any, Iterable


def _section(title: str, body: str) -> str:
    return f"## {title}\n{body.strip() or 'unknown'}\n"


def render_module_summary(module_name: str, summaries: list[dict[str, Any]], key_files: list[str]) -> str:
    purposes = [summary.get("purpose", "").strip() for summary in summaries if summary.get("purpose")]
    key_entities = [entity for summary in summaries for entity in summary.get("key_entities", [])]
    entrypoints = [entry.get("name", "") for summary in summaries for entry in summary.get("public_entrypoints", [])]
    configs = [config for summary in summaries for config in summary.get("configs_env", [])]
    errors = [error for summary in summaries for error in summary.get("errors_and_exceptions", [])]
    risks = [risk for summary in summaries for risk in summary.get("risks", [])]

    body = [
        f"# Module: {module_name}\n",
        _section("Purpose", "\n".join(f"- {p}" for p in purposes) if purposes else "unknown"),
        _section("Key Components", "\n".join(f"- {e}" for e in key_entities) if key_entities else "unknown"),
        _section("Entrypoints", "\n".join(f"- {e}" for e in entrypoints if e) if entrypoints else "unknown"),
        _section("Configs/Env", "\n".join(f"- {c}" for c in configs) if configs else "unknown"),
        _section("Data/Flow", "unknown"),
        _section("Errors/Resilience", "\n".join(f"- {e}" for e in errors) if errors else "unknown"),
        _section("Risks", "\n".join(f"- {r}" for r in risks) if risks else "unknown"),
        _section("key_files", "\n".join(f"- {path}" for path in key_files) if key_files else "unknown"),
    ]
    return "\n".join(body)


def render_project_overview(
    module_tree: dict[str, Any],
    module_summaries: dict[str, str],
    important_files: Iterable[str],
) -> str:
    module_lines = []
    for module in module_tree["modules"]:
        module_lines.append(f"- {module['name']} ({module['root_path']})")
    overview = [
        "# Project Overview\n",
        _section("Project Purpose", "unknown"),
        _section("Architecture (Modules)", "\n".join(module_lines) if module_lines else "unknown"),
        _section("Main Entrypoints", "unknown"),
        _section("Runtime/Deploy Hints", "unknown"),
        _section("Most important modules", "\n".join(module_lines[:5]) if module_lines else "unknown"),
        _section(
            "Most important files",
            "\n".join(f"- {path}" for path in important_files) if important_files else "unknown",
        ),
        _section("key_files", "\n".join(f"- {path}" for path in important_files) if important_files else "unknown"),
    ]
    return "\n".join(overview)


def render_view(
    aspect_title: str,
    summaries: list[dict[str, Any]],
    key_files: dict[str, list[str]],
) -> str:
    key_sections = []
    for group, files in key_files.items():
        items = "\n".join(f"- {path}" for path in files) if files else "- none"
        key_sections.append(f"### {group}\n{items}")
    key_files_block = "\n\n".join(key_sections) if key_sections else "- none"
    body = [
        f"# {aspect_title}\n",
        _section("What matters", "unknown"),
        _section("Key elements", "unknown"),
        _section("How it works", "unknown"),
        _section("Configs/Env", "unknown"),
        _section("Risks", "unknown"),
        _section("Open questions", "unknown"),
        _section("key_files", key_files_block),
    ]
    return "\n".join(body)
