from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sumagent_a import models
from sumagent_a.chunking import chunk_text
from sumagent_a.index import IndexData, IndexEntry
from sumagent_a.logging import RunLogger
from sumagent_a.scanner import FileInfo
from sumagent_a.textio import decode_bytes, is_binary_bytes, read_head_tail
from sumagent_a.utils import sha256_bytes, summary_filename


LANGUAGE_MAP = {
    ".py": "python",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".js": "js",
    ".ts": "ts",
    ".tsx": "ts",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "md",
    ".sql": "sql",
    ".sh": "shell",
    ".ps1": "shell",
    ".env": "shell",
    ".ini": "other",
    ".properties": "other",
}


@dataclass
class FileSummarizeConfig:
    max_file_bytes: int
    max_chunk_chars: int
    max_chunks_per_file: int
    overlap_chars: int
    head_tail_bytes: int
    null_byte_threshold: int
    non_printable_ratio_threshold: float
    prompt_system: str
    reduce_prompt: str


def detect_language(path: Path) -> models.Language:
    if path.name == "Dockerfile":
        return "shell"
    if path.suffix.lower() in LANGUAGE_MAP:
        return LANGUAGE_MAP[path.suffix.lower()]
    return "unknown"


def parse_llm_json(content: str) -> dict[str, Any] | None:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def normalize_summary(summary: dict[str, Any], *, default: models.FileSummary) -> models.FileSummary:
    return models.FileSummary(
        schema="FileSummary.v1",
        relative_path=summary.get("relative_path", default.relative_path),
        file_hash_sha256=summary.get("file_hash_sha256", default.file_hash_sha256),
        size_bytes=summary.get("size_bytes", default.size_bytes),
        language=summary.get("language", default.language),
        purpose=summary.get("purpose", default.purpose),
        key_entities=sorted(summary.get("key_entities", default.key_entities)),
        public_entrypoints=summary.get("public_entrypoints", default.public_entrypoints),
        external_dependencies=sorted(summary.get("external_dependencies", default.external_dependencies)),
        configs_env=sorted(summary.get("configs_env", default.configs_env)),
        errors_and_exceptions=sorted(summary.get("errors_and_exceptions", default.errors_and_exceptions)),
        todo_fixme=sorted(summary.get("todo_fixme", default.todo_fixme)),
        risks=sorted(summary.get("risks", default.risks)),
        evidence=summary.get("evidence", default.evidence),
        generated_at=models.utc_now_iso(),
    )


def build_file_prompt(
    *,
    relative_path: str,
    language_hint: str,
    content: str,
    chunk_info: str | None,
    system_prompt: str,
) -> str:
    chunk_note = f"\nChunk: {chunk_info}" if chunk_info else ""
    return (
        f"{system_prompt}\n"
        "Верни СТРОГО JSON по схеме FileSummary.v1. "
        "Если данных нет - используй null или пустые массивы.\n"
        f"Файл: {relative_path}\n"
        f"Язык: {language_hint}{chunk_note}\n"
        "Содержимое:\n"
        f"{content}"
    )


def build_reduce_prompt(partials: list[dict[str, Any]], reduce_prompt: str, relative_path: str) -> str:
    payload = json.dumps(partials, ensure_ascii=False, indent=2)
    return (
        "Собери итоговую микро-суммаризацию файла из набора частичных суммаризаций чанков. "
        "Верни только JSON по схеме FileSummary.v1.\n"
        f"Файл: {relative_path}\n"
        f"Инструкции: {reduce_prompt}\n"
        f"Чанки:\n{payload}"
    )


def summarize_files(
    *,
    files: list[FileInfo],
    repo_root: Path,
    out_dir: Path,
    index: IndexData,
    llm_client: Any,
    config: FileSummarizeConfig,
    run_logger: RunLogger,
    force: bool,
    dry_run: bool,
) -> None:
    files_dir = out_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    for info in files:
        run_logger.metrics.files_total += 1
        data = info.abs_path.read_bytes()
        if is_binary_bytes(data, config.null_byte_threshold, config.non_printable_ratio_threshold):
            run_logger.metrics.files_skipped_excluded += 1
            run_logger.log(
                level="info",
                event="file_binary",
                relative_path=info.relative_path,
                message="Binary file skipped.",
            )
            continue

        file_hash = sha256_bytes(data)
        previous = index.files.get(info.relative_path)
        summary_path = files_dir / summary_filename(info.relative_path)
        if (
            not force
            and previous
            and previous.file_hash_sha256 == file_hash
            and summary_path.exists()
        ):
            run_logger.metrics.files_skipped_cached += 1
            continue

        if dry_run:
            run_logger.log(
                level="info",
                event="file_dry_run",
                relative_path=info.relative_path,
                message="Dry run - skipping summarization.",
            )
            continue

        if info.size_bytes > config.max_file_bytes:
            text_result = read_head_tail(info.abs_path, config.head_tail_bytes)
        else:
            text_result = decode_bytes(data)

        if text_result is None:
            run_logger.metrics.errors_count += 1
            run_logger.log(
                level="error",
                event="decode_failed",
                relative_path=info.relative_path,
                message="Unable to decode file.",
            )
            continue

        language = detect_language(info.abs_path)
        content = text_result.text
        if len(content) > config.max_chunk_chars:
            chunks = chunk_text(
                content,
                max_chunk_chars=config.max_chunk_chars,
                overlap_chars=config.overlap_chars,
                max_chunks=config.max_chunks_per_file,
            )
            partials: list[dict[str, Any]] = []
            for chunk in chunks:
                prompt = build_file_prompt(
                    relative_path=info.relative_path,
                    language_hint=language,
                    content=chunk.text,
                    chunk_info=f"{chunk.index}/{chunk.total}",
                    system_prompt=config.prompt_system,
                )
                run_logger.metrics.llm_calls_count += 1
                response = llm_client.summarize(prompt)
                parsed = parse_llm_json(response)
                if parsed:
                    partials.append(parsed)
            reduce_prompt = build_reduce_prompt(partials, config.reduce_prompt, info.relative_path)
            run_logger.metrics.llm_calls_count += 1
            reduced = parse_llm_json(llm_client.summarize(reduce_prompt))
            default_summary = models.build_empty_file_summary(
                relative_path=info.relative_path,
                file_hash_sha256=file_hash,
                size_bytes=info.size_bytes,
                language=language,
                purpose="Unknown.",
            )
            summary = normalize_summary(reduced or {}, default=default_summary)
        else:
            prompt = build_file_prompt(
                relative_path=info.relative_path,
                language_hint=language,
                content=content,
                chunk_info=None,
                system_prompt=config.prompt_system,
            )
            run_logger.metrics.llm_calls_count += 1
            response = llm_client.summarize(prompt)
            parsed = parse_llm_json(response)
            default_summary = models.build_empty_file_summary(
                relative_path=info.relative_path,
                file_hash_sha256=file_hash,
                size_bytes=info.size_bytes,
                language=language,
                purpose="Unknown.",
            )
            summary = normalize_summary(parsed or {}, default=default_summary)

        summary_path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        index.files[info.relative_path] = IndexEntry(
            file_hash_sha256=file_hash,
            summary_path=str(summary_path.relative_to(out_dir)),
            size_bytes=info.size_bytes,
            mtime=info.mtime,
        )
        run_logger.metrics.files_summarized += 1
