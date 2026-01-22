import json
import shutil
from pathlib import Path

from sumagent_a.index import load_index, new_index, save_index
from sumagent_a.logging import RunLogger
from sumagent_a.scanner import scan_repo
from sumagent_a.summarize_dirs import DirSummarizeConfig, summarize_dirs
from sumagent_a.summarize_files import FileSummarizeConfig, summarize_files


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    def summarize(self, prompt: str) -> str:
        self.calls += 1
        if "DirSummary.v1" in prompt:
            return json.dumps(
                {
                    "schema": "DirSummary.v1",
                    "relative_path": ".",
                    "dir_hash_sha256": "",
                    "purpose": "Dir summary",
                    "contents_overview": "",
                    "key_components": [],
                    "entrypoints": [],
                    "generated_at": "",
                }
            )
        return json.dumps(
            {
                "schema": "FileSummary.v1",
                "relative_path": "unknown",
                "file_hash_sha256": "",
                "size_bytes": 0,
                "language": "unknown",
                "purpose": "File summary",
                "key_entities": [],
                "public_entrypoints": [],
                "external_dependencies": [],
                "configs_env": [],
                "errors_and_exceptions": [],
                "todo_fixme": [],
                "risks": [],
                "evidence": [],
                "generated_at": "",
            }
        )


def test_incremental_skips_unchanged(tmp_path: Path) -> None:
    fixture_root = Path(__file__).parent / "fixtures" / "sample_repo"
    repo_root = tmp_path / "repo"
    shutil.copytree(fixture_root, repo_root)

    out_dir = repo_root / ".summary"
    config_files = FileSummarizeConfig(
        max_file_bytes=1024 * 1024,
        max_chunk_chars=24000,
        max_chunks_per_file=24,
        overlap_chars=400,
        head_tail_bytes=20000,
        null_byte_threshold=1,
        non_printable_ratio_threshold=0.3,
        prompt_system="sys",
        reduce_prompt="reduce",
    )
    config_dirs = DirSummarizeConfig(prompt_system="sys")

    files, dirs = scan_repo(repo_root, dir_exclusions=[".summary", "node_modules"], file_globs=["*.bin"])
    index = new_index(repo_root)
    llm = FakeLLM()
    run_logger = RunLogger(out_dir=out_dir)

    summarize_files(
        files=files,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index,
        llm_client=llm,
        config=config_files,
        run_logger=run_logger,
        force=False,
        dry_run=False,
    )
    summarize_dirs(
        dirs=dirs,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index,
        llm_client=llm,
        config=config_dirs,
        run_logger=run_logger,
        force=False,
        dry_run=False,
    )
    save_index(out_dir / "index.json", index)
    assert llm.calls > 0

    llm_second = FakeLLM()
    run_logger_second = RunLogger(out_dir=out_dir)
    index_second = load_index(out_dir / "index.json")
    assert index_second is not None

    summarize_files(
        files=files,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index_second,
        llm_client=llm_second,
        config=config_files,
        run_logger=run_logger_second,
        force=False,
        dry_run=False,
    )
    summarize_dirs(
        dirs=dirs,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index_second,
        llm_client=llm_second,
        config=config_dirs,
        run_logger=run_logger_second,
        force=False,
        dry_run=False,
    )

    assert llm_second.calls == 0

    target_file = repo_root / "app.py"
    target_file.write_text("print('changed')\n", encoding="utf-8")

    files_updated, dirs_updated = scan_repo(
        repo_root, dir_exclusions=[".summary", "node_modules"], file_globs=["*.bin"]
    )
    index_third = load_index(out_dir / "index.json")
    assert index_third is not None

    llm_third = FakeLLM()
    run_logger_third = RunLogger(out_dir=out_dir)
    summarize_files(
        files=files_updated,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index_third,
        llm_client=llm_third,
        config=config_files,
        run_logger=run_logger_third,
        force=False,
        dry_run=False,
    )
    summarize_dirs(
        dirs=dirs_updated,
        repo_root=repo_root,
        out_dir=out_dir,
        index=index_third,
        llm_client=llm_third,
        config=config_dirs,
        run_logger=run_logger_third,
        force=False,
        dry_run=False,
    )

    assert llm_third.calls > 0
    assert index_third.files["app.py"].file_hash_sha256 != index.files["app.py"].file_hash_sha256
