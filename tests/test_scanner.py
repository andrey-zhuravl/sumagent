from pathlib import Path

from sumagent_a.cli import DEFAULT_CONFIG
from sumagent_a.scanner import scan_repo


def test_scanner_excludes_dirs_and_files() -> None:
    repo_root = Path(__file__).parent / "fixtures" / "sample_repo"
    files, dirs = scan_repo(
        repo_root,
        dir_exclusions=DEFAULT_CONFIG["exclusions"]["dir_names"],
        file_globs=DEFAULT_CONFIG["exclusions"]["file_globs"],
    )
    file_paths = {file.relative_path for file in files}
    dir_paths = {dir_info.relative_path for dir_info in dirs}

    assert "node_modules/ignored.js" not in file_paths
    assert ".summary" not in dir_paths
    assert "app.py" in file_paths
    assert "subdir/config.json" in file_paths
