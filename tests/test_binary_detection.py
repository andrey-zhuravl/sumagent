from pathlib import Path

from sumagent_a.textio import is_binary_bytes


def test_binary_detection() -> None:
    repo_root = Path(__file__).parent / "fixtures" / "sample_repo"
    data = (repo_root / "binary.txt").read_bytes()
    assert is_binary_bytes(data, null_byte_threshold=1, non_printable_ratio=0.3)
