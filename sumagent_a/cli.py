from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sumagent_a.index import load_index, new_index, save_index
from sumagent_a.llm_client import LLMClient, LLMConfig
from sumagent_a.logging import RunLogger
from sumagent_a.scanner import scan_repo
from sumagent_a.summarize_dirs import DirSummarizeConfig, summarize_dirs
from sumagent_a.summarize_files import FileSummarizeConfig, summarize_files
from sumagent_a.utils import ensure_within_repo, resolve_out_dir


DEFAULT_CONFIG: dict[str, Any] = {
    "exclusions": {
        "dir_names": [
            ".git",
            ".idea",
            ".vscode",
            ".summary",
            ".venv",
            "venv",
            "node_modules",
            "dist",
            "build",
            "target",
            "out",
            "__pycache__",
        ],
        "file_globs": [
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.gif",
            "*.webp",
            "*.pdf",
            "*.zip",
            "*.7z",
            "*.tar",
            "*.gz",
            "*.jar",
            "*.class",
            "*.exe",
            "*.dll",
            "*.so",
            "*.dylib",
            "*.bin",
            "*.wasm",
        ],
        "max_file_bytes_default": 1048576,
        "head_tail_bytes": 20000,
    },
    "file_type_handling": {
        "binary_detection": {
            "null_byte_threshold": 1,
            "non_printable_ratio_threshold": 0.3,
        }
    },
    "chunking_strategy": {
        "max_chunk_chars": 24000,
        "max_chunks_per_file": 24,
        "overlap_chars": 400,
        "aggregation": {
            "reduce_prompt": "Собери итоговую микро-суммаризацию файла из набора частичных суммаризаций чанков. Не добавляй фактов, которых нет в чанках.",
        },
    },
    "prompting": {
        "system": "Ты помощник, который делает краткие технические микро-суммаризации файлов проекта. Нельзя выдумывать факты. Если чего-то нет в тексте — пиши unknown/не найдено.",
    },
    "llm": {
        "base_url": "http://localhost:8000/v1",
        "model": "Qwen3-4B-Instruct",
        "max_output_tokens": 900,
        "temperature": 0.2,
        "timeouts": {
            "total_s": 180,
        },
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: Path | None) -> dict[str, Any]:
    if config_path and config_path.exists():
        config_data = json.loads(config_path.read_text(encoding="utf-8"))
        return deep_merge(DEFAULT_CONFIG, config_data)
    return DEFAULT_CONFIG


def build_llm_client(config: dict[str, Any]) -> LLMClient:
    llm = config["llm"]
    timeout_s = int(llm.get("timeouts", {}).get("total_s", 180))
    return LLMClient(
        LLMConfig(
            base_url=llm["base_url"],
            model=llm["model"],
            max_output_tokens=int(llm["max_output_tokens"]),
            temperature=float(llm["temperature"]),
            timeout_s=timeout_s,
        )
    )


def handle_summarize(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo).resolve()
    config = load_config(Path(args.config).resolve() if args.config else None)
    out_dir = resolve_out_dir(repo_root, args.out)
    out_dir = out_dir.resolve()
    if not Path(args.out).is_absolute():
        ensure_within_repo(repo_root, out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    ensure_within_repo(repo_root, repo_root)

    index_path = out_dir / "index.json"
    index = load_index(index_path) or new_index(repo_root)

    run_logger = RunLogger(out_dir=out_dir)

    files, dirs = scan_repo(
        repo_root,
        dir_exclusions=config["exclusions"]["dir_names"],
        file_globs=config["exclusions"]["file_globs"],
    )

    llm_client = build_llm_client(config)

    summarize_files(
        files=files,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index,
        llm_client=llm_client,
        config=FileSummarizeConfig(
            max_file_bytes=int(args.max_file_bytes),
            max_chunk_chars=int(args.max_chunk_chars),
            max_chunks_per_file=int(args.max_chunks_per_file),
            overlap_chars=int(config["chunking_strategy"]["overlap_chars"]),
            head_tail_bytes=int(config["exclusions"]["head_tail_bytes"]),
            null_byte_threshold=int(config["file_type_handling"]["binary_detection"]["null_byte_threshold"]),
            non_printable_ratio_threshold=float(
                config["file_type_handling"]["binary_detection"]["non_printable_ratio_threshold"]
            ),
            prompt_system=config["prompting"]["system"],
            reduce_prompt=config["chunking_strategy"]["aggregation"]["reduce_prompt"],
        ),
        run_logger=run_logger,
        force=args.force,
        dry_run=args.dry_run,
    )

    summarize_dirs(
        dirs=dirs,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index,
        llm_client=llm_client,
        config=DirSummarizeConfig(prompt_system=config["prompting"]["system"]),
        run_logger=run_logger,
        force=args.force,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        save_index(index_path, index)
        run_logger.flush()


def handle_summarize_file(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo).resolve()
    out_dir = resolve_out_dir(repo_root, args.out)
    out_dir = out_dir.resolve()
    if not Path(args.out).is_absolute():
        ensure_within_repo(repo_root, out_dir)

    config = load_config(Path(args.config).resolve() if args.config else None)
    index_path = out_dir / "index.json"
    index = load_index(index_path) or new_index(repo_root)
    run_logger = RunLogger(out_dir=out_dir)
    llm_client = build_llm_client(config)

    target = (repo_root / args.path).resolve()
    ensure_within_repo(repo_root, target)

    files, _ = scan_repo(
        repo_root,
        dir_exclusions=config["exclusions"]["dir_names"],
        file_globs=config["exclusions"]["file_globs"],
    )
    filtered = [info for info in files if info.abs_path == target]

    summarize_files(
        files=filtered,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index,
        llm_client=llm_client,
        config=FileSummarizeConfig(
            max_file_bytes=int(config["exclusions"]["max_file_bytes_default"]),
            max_chunk_chars=int(config["chunking_strategy"]["max_chunk_chars"]),
            max_chunks_per_file=int(config["chunking_strategy"]["max_chunks_per_file"]),
            overlap_chars=int(config["chunking_strategy"]["overlap_chars"]),
            head_tail_bytes=int(config["exclusions"]["head_tail_bytes"]),
            null_byte_threshold=int(config["file_type_handling"]["binary_detection"]["null_byte_threshold"]),
            non_printable_ratio_threshold=float(
                config["file_type_handling"]["binary_detection"]["non_printable_ratio_threshold"]
            ),
            prompt_system=config["prompting"]["system"],
            reduce_prompt=config["chunking_strategy"]["aggregation"]["reduce_prompt"],
        ),
        run_logger=run_logger,
        force=args.force,
        dry_run=False,
    )
    save_index(index_path, index)
    run_logger.flush()


def handle_summarize_dir(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo).resolve()
    out_dir = resolve_out_dir(repo_root, args.out)
    out_dir = out_dir.resolve()
    if not Path(args.out).is_absolute():
        ensure_within_repo(repo_root, out_dir)

    config = load_config(Path(args.config).resolve() if args.config else None)
    index_path = out_dir / "index.json"
    index = load_index(index_path) or new_index(repo_root)
    run_logger = RunLogger(out_dir=out_dir)
    llm_client = build_llm_client(config)

    target = (repo_root / args.path).resolve()
    ensure_within_repo(repo_root, target)

    _, dirs = scan_repo(
        repo_root,
        dir_exclusions=config["exclusions"]["dir_names"],
        file_globs=config["exclusions"]["file_globs"],
    )
    rel_target = target.relative_to(repo_root).as_posix() if target != repo_root else "."
    filtered = [info for info in dirs if info.relative_path == rel_target]

    summarize_dirs(
        dirs=filtered,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index,
        llm_client=llm_client,
        config=DirSummarizeConfig(prompt_system=config["prompting"]["system"]),
        run_logger=run_logger,
        force=args.force,
        dry_run=False,
    )
    save_index(index_path, index)
    run_logger.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage A summarizer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize_parser = subparsers.add_parser("summarize", help="Run full summarization")
    summarize_parser.add_argument("--repo", required=True)
    summarize_parser.add_argument("--out", default=".summary")
    summarize_parser.add_argument("--config")
    summarize_parser.add_argument("--force", action="store_true")
    summarize_parser.add_argument("--dry-run", action="store_true")
    summarize_parser.add_argument("--concurrency", type=int, default=1)
    summarize_parser.add_argument("--max-file-bytes", type=int, default=1048576)
    summarize_parser.add_argument("--max-chunk-chars", type=int, default=24000)
    summarize_parser.add_argument("--max-chunks-per-file", type=int, default=24)
    summarize_parser.set_defaults(func=handle_summarize)

    summarize_file_parser = subparsers.add_parser("summarize-file", help="Summarize single file")
    summarize_file_parser.add_argument("--repo", required=True)
    summarize_file_parser.add_argument("--path", required=True)
    summarize_file_parser.add_argument("--out", default=".summary")
    summarize_file_parser.add_argument("--config")
    summarize_file_parser.add_argument("--force", action="store_true")
    summarize_file_parser.set_defaults(func=handle_summarize_file)

    summarize_dir_parser = subparsers.add_parser("summarize-dir", help="Summarize single directory")
    summarize_dir_parser.add_argument("--repo", required=True)
    summarize_dir_parser.add_argument("--path", required=True)
    summarize_dir_parser.add_argument("--out", default=".summary")
    summarize_dir_parser.add_argument("--config")
    summarize_dir_parser.add_argument("--force", action="store_true")
    summarize_dir_parser.set_defaults(func=handle_summarize_dir)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
