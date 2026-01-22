from pathlib import Path

from sumagent_b.load_stage_a import load_stage_a
from sumagent_b.module_tree import build_module_tree, module_id_for_path


def test_module_tree_builds_stable_ids() -> None:
    summary_dir = Path(__file__).parent / "fixtures" / "sample_summary_a"
    stage_a = load_stage_a(summary_dir)

    module_tree = build_module_tree(stage_a.index.files.keys())

    src_id = module_id_for_path("src")
    config_id = module_id_for_path("config")

    module_ids = {module["module_id"] for module in module_tree["modules"]}
    assert src_id in module_ids
    assert config_id in module_ids

    assert module_tree["path_to_module"]["src/auth.py"] == src_id
    assert module_tree["path_to_module"]["config/docker.yaml"] == config_id
