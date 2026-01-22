from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .generate_modules import generate_modules
from .generate_overview import generate_project_overview
from .generate_views import ASPECTS, generate_views, select_files_for_aspects
from .incremental import plan_modules, plan_views
from .index import load_stage_b_index, new_stage_b_index, save_stage_b_index
from .llm_client import LLMClient, LLMConfig
from .load_stage_a import load_stage_a
from .logging import RunLogger
from .module_tree import build_module_tree, modules_topological


@dataclass
class Config:
    ignore_paths: list[str]
    label_paths: dict[str, list[str]]
    llm_base_url: str
    llm_model: str
    max_items_per_llm_batch: int
    max_chars_per_llm_batch: int


DEFAULT_CONFIG = Config(
    ignore_paths=[".summary", "node_modules"],
    label_paths={},
    llm_base_url="http://localhost:8000/v1",
    llm_model="Qwen3-4B-Instruct",
    max_items_per_llm_batch=80,
    max_chars_per_llm_batch=24000,
)


def load_config(path: Path | None) -> Config:
    if path is None or not path.exists():
        return DEFAULT_CONFIG
    data = json.loads(path.read_text(encoding="utf-8"))
    return Config(
        ignore_paths=data.get("ignore_paths", DEFAULT_CONFIG.ignore_paths),
        label_paths=data.get("label_paths", DEFAULT_CONFIG.label_paths),
        llm_base_url=data.get("llm", {}).get("base_url", DEFAULT_CONFIG.llm_base_url),
        llm_model=data.get("llm", {}).get("model", DEFAULT_CONFIG.llm_model),
        max_items_per_llm_batch=data.get("max_items_per_llm_batch", DEFAULT_CONFIG.max_items_per_llm_batch),
        max_chars_per_llm_batch=data.get("max_chars_per_llm_batch", DEFAULT_CONFIG.max_chars_per_llm_batch),
    )


def build_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo)
    summary_dir = Path(args.summary_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(Path(args.config) if args.config else None)

    stage_a = load_stage_a(summary_dir)
    file_paths = list(stage_a.index.files.keys())
    module_tree = build_module_tree(file_paths, ignore_paths=config.ignore_paths, label_paths=config.label_paths)
    module_tree["repo_root"] = str(repo_root)
    module_tree["generated_at"] = datetime.now(timezone.utc).isoformat()

    stage_b_index_path = out_dir / "cache" / "stage_b_index.json"
    stage_b_index = load_stage_b_index(stage_b_index_path) or new_stage_b_index()

    selected_by_aspect = select_files_for_aspects(stage_a.file_summaries)
    module_plans = plan_modules(module_tree, stage_a.file_summaries, stage_b_index.modules, force=args.force)
    view_plans = plan_views(ASPECTS, selected_by_aspect, stage_b_index.views, force=args.force)

    run_logger = RunLogger(out_dir=out_dir)
    run_logger.metrics.modules_total = len(module_tree["modules"])
    run_logger.metrics.views_total = len(ASPECTS)
    run_logger.metrics.modules_dirty = sum(1 for plan in module_plans.values() if plan.dirty)
    run_logger.metrics.views_dirty = sum(1 for plan in view_plans.values() if plan.dirty)

    llm_client = None if args.dry_run else LLMClient(LLMConfig(base_url=config.llm_base_url, model=config.llm_model))

    module_results = generate_modules(
        module_tree=module_tree,
        file_summaries=stage_a.file_summaries,
        module_plans=module_plans,
        out_dir=out_dir,
        llm_client=llm_client,
        run_logger=run_logger,
        dry_run=args.dry_run,
    )

    generate_project_overview(
        module_tree=module_tree,
        module_results=module_results,
        file_summaries=stage_a.file_summaries,
        out_dir=out_dir,
        llm_client=llm_client,
        dry_run=args.dry_run,
    )

    generate_views(
        selected_by_aspect=selected_by_aspect,
        view_plans=view_plans,
        out_dir=out_dir,
        llm_client=llm_client,
        run_logger=run_logger,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        (out_dir / "cache").mkdir(parents=True, exist_ok=True)
        (out_dir / "modules").mkdir(parents=True, exist_ok=True)
        (out_dir / "views").mkdir(parents=True, exist_ok=True)
        module_tree_path = out_dir / "module_tree.json"
        module_tree_path.write_text(json.dumps(module_tree, ensure_ascii=False, indent=2), encoding="utf-8")

        stage_b_index.modules = {
            module_id: {
                "module_input_hash": plan.module_input_hash,
                "module_summary_path": str(Path("modules") / f"{module_id}.md"),
            }
            for module_id, plan in module_plans.items()
        }
        stage_b_index.views = {
            aspect_id: {
                "aspect_input_hash": plan.aspect_input_hash,
                "view_path": str(Path("views") / f"{aspect_id}.md"),
            }
            for aspect_id, plan in view_plans.items()
        }
        save_stage_b_index(stage_b_index_path, stage_b_index)

    return 0


def build_view_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo)
    summary_dir = Path(args.summary_dir)
    out_dir = Path(args.out)
    config = load_config(Path(args.config) if args.config else None)
    stage_a = load_stage_a(summary_dir)
    file_paths = list(stage_a.index.files.keys())
    module_tree = build_module_tree(file_paths, ignore_paths=config.ignore_paths, label_paths=config.label_paths)
    module_tree["repo_root"] = str(repo_root)
    module_tree["generated_at"] = datetime.now(timezone.utc).isoformat()

    stage_b_index_path = out_dir / "cache" / "stage_b_index.json"
    stage_b_index = load_stage_b_index(stage_b_index_path) or new_stage_b_index()

    selected_by_aspect = select_files_for_aspects(stage_a.file_summaries)
    view_plans = plan_views(ASPECTS, selected_by_aspect, stage_b_index.views, force=args.force)
    run_logger = RunLogger(out_dir=out_dir)

    llm_client = None if args.dry_run else LLMClient(LLMConfig(base_url=config.llm_base_url, model=config.llm_model))

    view_plans = {args.aspect: view_plans[args.aspect]} if args.aspect in view_plans else {}

    generate_views(
        selected_by_aspect=selected_by_aspect,
        view_plans=view_plans,
        out_dir=out_dir,
        llm_client=llm_client,
        run_logger=run_logger,
        dry_run=args.dry_run,
    )
    return 0


def build_module_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo)
    summary_dir = Path(args.summary_dir)
    out_dir = Path(args.out)
    config = load_config(Path(args.config) if args.config else None)
    stage_a = load_stage_a(summary_dir)
    file_paths = list(stage_a.index.files.keys())
    module_tree = build_module_tree(file_paths, ignore_paths=config.ignore_paths, label_paths=config.label_paths)
    module_tree["repo_root"] = str(repo_root)
    module_tree["generated_at"] = datetime.now(timezone.utc).isoformat()

    stage_b_index_path = out_dir / "cache" / "stage_b_index.json"
    stage_b_index = load_stage_b_index(stage_b_index_path) or new_stage_b_index()

    module_plans = plan_modules(module_tree, stage_a.file_summaries, stage_b_index.modules, force=args.force)
    run_logger = RunLogger(out_dir=out_dir)

    llm_client = None if args.dry_run else LLMClient(LLMConfig(base_url=config.llm_base_url, model=config.llm_model))

    target_root = args.module_root
    target_module = None
    for module in module_tree["modules"]:
        if module["root_path"] == target_root:
            target_module = module["module_id"]
            break
    module_plans = {target_module: module_plans[target_module]} if target_module else {}

    generate_modules(
        module_tree=module_tree,
        file_summaries=stage_a.file_summaries,
        module_plans=module_plans,
        out_dir=out_dir,
        llm_client=llm_client,
        run_logger=run_logger,
        dry_run=args.dry_run,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sumagent Stage B")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Run full Stage B pipeline")
    build_parser.add_argument("--repo", required=True)
    build_parser.add_argument("--summary-dir", default=".summary")
    build_parser.add_argument("--out", default=".summary/project")
    build_parser.add_argument("--config", default=None)
    build_parser.add_argument("--force", action="store_true")
    build_parser.add_argument("--dry-run", action="store_true")
    build_parser.add_argument("--concurrency", type=int, default=1)
    build_parser.set_defaults(func=build_command)

    view_parser = subparsers.add_parser("build-view", help="Rebuild one aspect view")
    view_parser.add_argument("--repo", required=True)
    view_parser.add_argument("--summary-dir", default=".summary")
    view_parser.add_argument("--out", default=".summary/project")
    view_parser.add_argument("--config", default=None)
    view_parser.add_argument("--aspect", required=True)
    view_parser.add_argument("--force", action="store_true")
    view_parser.add_argument("--dry-run", action="store_true")
    view_parser.set_defaults(func=build_view_command)

    module_parser = subparsers.add_parser("build-module", help="Rebuild one module")
    module_parser.add_argument("--repo", required=True)
    module_parser.add_argument("--summary-dir", default=".summary")
    module_parser.add_argument("--out", default=".summary/project")
    module_parser.add_argument("--config", default=None)
    module_parser.add_argument("--module-root", required=True)
    module_parser.add_argument("--force", action="store_true")
    module_parser.add_argument("--dry-run", action="store_true")
    module_parser.set_defaults(func=build_module_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)
