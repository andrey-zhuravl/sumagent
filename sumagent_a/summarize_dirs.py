from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sumagent_a import models
from sumagent_a.index import DirIndexEntry, IndexData
from sumagent_a.logging import RunLogger
from sumagent_a.scanner import DirInfo
from sumagent_a.utils import sha256_text, summary_filename


@dataclass
class DirSummarizeConfig:
    prompt_system: str


def build_dir_prompt(
    *,
    relative_path: str,
    child_file_summaries: list[dict[str, Any]],
    child_dir_summaries: list[dict[str, Any]],
    system_prompt: str,
) -> str:
    payload = json.dumps(
        {
            "child_file_summaries": child_file_summaries,
            "child_dir_summaries": child_dir_summaries,
        },
        ensure_ascii=False,
        indent=2,
    )
    return (
        f"{system_prompt}\n"
        "Верни СТРОГО JSON по схеме DirSummary.v1.\n"
        f"Директория: {relative_path}\n"
        f"Данные:\n{payload}"
    )


def dir_hash(child_file_entries: list[tuple[str, str]], child_dir_entries: list[tuple[str, str]]) -> str:
    entries = [f"F:{path}:{file_hash}" for path, file_hash in child_file_entries] + [
        f"D:{path}:{dir_hash_value}" for path, dir_hash_value in child_dir_entries
    ]
    return sha256_text("\n".join(sorted(entries)))


def summarize_dirs(
    *,
    dirs: list[DirInfo],
    repo_root: Path,
    out_dir: Path,
    index: IndexData,
    llm_client: Any,
    config: DirSummarizeConfig,
    run_logger: RunLogger,
    force: bool,
    dry_run: bool,
) -> None:
    dirs_dir = out_dir / "dirs"
    dirs_dir.mkdir(parents=True, exist_ok=True)

    dir_map = {dir_info.relative_path: dir_info for dir_info in dirs}
    sorted_dirs = sorted(dir_map.values(), key=lambda d: len(Path(d.relative_path).parts), reverse=True)

    for dir_info in sorted_dirs:
        child_files = {
            path: entry
            for path, entry in index.files.items()
            if Path(path).parent.as_posix() == dir_info.relative_path
        }
        child_dirs = {
            path: entry
            for path, entry in index.dirs.items()
            if Path(path).parent.as_posix() == dir_info.relative_path and path != dir_info.relative_path
        }
        file_entries = sorted([(path, entry.file_hash_sha256) for path, entry in child_files.items()])
        dir_entries = sorted([(path, entry.dir_hash_sha256) for path, entry in child_dirs.items()])
        current_hash = dir_hash(file_entries, dir_entries)

        summary_path = dirs_dir / summary_filename(dir_info.relative_path)
        previous = index.dirs.get(dir_info.relative_path)
        if (
            not force
            and previous
            and previous.dir_hash_sha256 == current_hash
            and summary_path.exists()
        ):
            continue

        if dry_run:
            run_logger.log(
                level="info",
                event="dir_dry_run",
                relative_path=dir_info.relative_path,
                message="Dry run - skipping dir summarization.",
            )
            continue

        child_file_summaries: list[dict[str, Any]] = []
        for path, entry in child_files.items():
            summary_path_file = out_dir / entry.summary_path
            if summary_path_file.exists():
                child_file_summaries.append(json.loads(summary_path_file.read_text(encoding="utf-8")))

        child_dir_summaries: list[dict[str, Any]] = []
        for path, entry in child_dirs.items():
            summary_path_dir = out_dir / entry.summary_path
            if summary_path_dir.exists():
                child_dir_summaries.append(json.loads(summary_path_dir.read_text(encoding="utf-8")))

        prompt = build_dir_prompt(
            relative_path=dir_info.relative_path,
            child_file_summaries=child_file_summaries,
            child_dir_summaries=child_dir_summaries,
            system_prompt=config.prompt_system,
        )
        run_logger.metrics.llm_calls_count += 1
        response = llm_client.summarize(prompt)
        try:
            parsed = json.loads(response) if response.strip().startswith("{") else {}
        except json.JSONDecodeError:
            parsed = {}
        default_summary = models.build_empty_dir_summary(
            relative_path=dir_info.relative_path,
            dir_hash_sha256=current_hash,
            purpose="Unknown.",
            contents_overview="",
        )
        summary = models.DirSummary(
            schema="DirSummary.v1",
            relative_path=parsed.get("relative_path", default_summary.relative_path),
            dir_hash_sha256=parsed.get("dir_hash_sha256", default_summary.dir_hash_sha256),
            purpose=parsed.get("purpose", default_summary.purpose),
            contents_overview=parsed.get("contents_overview", default_summary.contents_overview),
            key_components=parsed.get("key_components", default_summary.key_components),
            entrypoints=parsed.get("entrypoints", default_summary.entrypoints),
            generated_at=models.utc_now_iso(),
        )

        summary_path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        index.dirs[dir_info.relative_path] = DirIndexEntry(
            dir_hash_sha256=current_hash,
            summary_path=str(summary_path.relative_to(out_dir)),
            mtime=dir_info.mtime,
        )
