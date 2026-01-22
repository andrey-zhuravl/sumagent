from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm_client import LLMClient
from .logging import RunLogger
from .render import render_view


ASPECTS = [
    {
        "id": "business_logic",
        "title": "Business Logic",
        "focus": "Основные доменные сущности, правила, сценарии, операции.",
    },
    {
        "id": "security_auth",
        "title": "Security & Auth",
        "focus": "Аутентификация/авторизация, права, секреты, токены, политики.",
    },
    {
        "id": "errors_resilience",
        "title": "Errors & Resilience",
        "focus": "Обработка ошибок, ретраи, таймауты, fallback, устойчивость.",
    },
    {
        "id": "concurrency_async",
        "title": "Concurrency / Async",
        "focus": "Параллелизм, корутины/потоки, блокировки, очереди задач.",
    },
    {
        "id": "data_streams_events",
        "title": "Data Streams / Events",
        "focus": "Kafka/очереди, топики, события, пайплайны данных.",
    },
    {
        "id": "deploy_config",
        "title": "Deploy / Config",
        "focus": "Конфигурации, переменные окружения, docker/k8s, сборка.",
    },
    {
        "id": "user_cases",
        "title": "User Cases",
        "focus": "Сценарии использования, внешние интерфейсы, API точки входа.",
    },
]

PATTERNS_BY_ASPECT = {
    "security_auth": [
        "auth",
        "security",
        "jwt",
        "oauth",
        "acl",
        "permission",
        "role",
        "rbac",
        "csrf",
        "cors",
        "secret",
        "token",
    ],
    "errors_resilience": ["retry", "timeout", "circuit", "fallback", "exception", "error", "resilience"],
    "concurrency_async": ["async", "await", "coroutine", "thread", "lock", "pool", "queue", "scheduler"],
    "data_streams_events": [
        "kafka",
        "topic",
        "event",
        "stream",
        "consumer",
        "producer",
        "message",
    ],
    "deploy_config": ["docker", "k8s", "helm", "compose", "yaml", "env", "config", "properties"],
    "user_cases": ["controller", "endpoint", "route", "handler", "api", "cli"],
    "business_logic": ["service", "domain", "usecase", "workflow", "operation", "rule"],
}


@dataclass
class ViewResult:
    aspect_id: str
    path: Path
    key_files: list[str]


def _summary_matches(summary: dict[str, Any], patterns: list[str]) -> bool:
    fields = [
        summary.get("relative_path", ""),
        summary.get("purpose", ""),
        " ".join(summary.get("key_entities", [])),
        " ".join(summary.get("external_dependencies", [])),
        " ".join(summary.get("configs_env", [])),
        " ".join(summary.get("errors_and_exceptions", [])),
        " ".join(summary.get("todo_fixme", [])),
        " ".join(summary.get("risks", [])),
    ]
    haystack = " ".join(fields).lower()
    return any(pattern in haystack for pattern in patterns)


def select_files_for_aspects(
    file_summaries: dict[str, dict[str, Any]],
    *,
    max_files_default: int = 120,
) -> dict[str, list[dict[str, Any]]]:
    selections: dict[str, list[dict[str, Any]]] = {}
    for aspect in ASPECTS:
        aspect_id = aspect["id"]
        patterns = PATTERNS_BY_ASPECT.get(aspect_id, [])
        matched = [summary for summary in file_summaries.values() if _summary_matches(summary, patterns)]
        matched_sorted = sorted(matched, key=lambda summary: summary.get("relative_path", ""))
        selections[aspect_id] = matched_sorted[:max_files_default]
    return selections


def generate_views(
    *,
    selected_by_aspect: dict[str, list[dict[str, Any]]],
    view_plans: dict[str, Any],
    out_dir: Path,
    llm_client: LLMClient | None,
    run_logger: RunLogger,
    dry_run: bool,
) -> dict[str, ViewResult]:
    views_dir = out_dir / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, ViewResult] = {}

    for aspect in ASPECTS:
        aspect_id = aspect["id"]
        plan = view_plans.get(aspect_id)
        if plan is None or not plan.dirty:
            continue
        summaries = selected_by_aspect.get(aspect_id, [])
        key_files = sorted({summary["relative_path"] for summary in summaries})
        if dry_run:
            content = ""
        elif llm_client:
            prompt = f"Aspect {aspect['title']}\nFiles: {', '.join(key_files)}"
            content = llm_client.summarize(prompt)
            run_logger.metrics.llm_calls_count += 1
        else:
            content = render_view(aspect["title"], summaries, {"key_files": key_files})
        if "key_files" not in content:
            content = f"{content}\n\n## key_files\n" + "\n".join(f"- {path}" for path in key_files)
        path = views_dir / f"{aspect_id}.md"
        if not dry_run:
            path.write_text(content, encoding="utf-8")
        results[aspect_id] = ViewResult(aspect_id=aspect_id, path=path, key_files=key_files)
        run_logger.metrics.views_built += 1
    return results
