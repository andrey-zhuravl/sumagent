from pathlib import Path

from sumagent_b.generate_views import ASPECTS, select_files_for_aspects
from sumagent_b.incremental import plan_modules, plan_views
from sumagent_b.load_stage_a import load_stage_a
from sumagent_b.module_tree import build_module_tree


def test_incremental_skips_unchanged_and_marks_dirty() -> None:
    summary_dir = Path(__file__).parent / "fixtures" / "sample_summary_a"
    stage_a = load_stage_a(summary_dir)
    module_tree = build_module_tree(stage_a.index.files.keys())

    selected = select_files_for_aspects(stage_a.file_summaries)

    first_module_plans = plan_modules(module_tree, stage_a.file_summaries, {})
    first_view_plans = plan_views(ASPECTS, selected, {})

    prev_modules = {
        module_id: {"module_input_hash": plan.module_input_hash, "module_summary_path": "modules/x.md"}
        for module_id, plan in first_module_plans.items()
    }
    prev_views = {
        aspect_id: {"aspect_input_hash": plan.aspect_input_hash, "view_path": "views/x.md"}
        for aspect_id, plan in first_view_plans.items()
    }

    second_module_plans = plan_modules(module_tree, stage_a.file_summaries, prev_modules)
    second_view_plans = plan_views(ASPECTS, selected, prev_views)

    assert all(not plan.dirty for plan in second_module_plans.values())
    assert all(not plan.dirty for plan in second_view_plans.values())

    mutated = dict(stage_a.file_summaries)
    updated = dict(mutated["src/auth.py"])
    updated["file_hash_sha256"] = "hash-auth-changed"
    mutated["src/auth.py"] = updated

    changed_module_plans = plan_modules(module_tree, mutated, prev_modules)
    changed_view_plans = plan_views(ASPECTS, select_files_for_aspects(mutated), prev_views)

    assert any(plan.dirty for plan in changed_module_plans.values())
    assert changed_view_plans["security_auth"].dirty is True
