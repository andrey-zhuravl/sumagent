from pathlib import Path

from sumagent_b.generate_overview import generate_project_overview
from sumagent_b.generate_views import generate_views, select_files_for_aspects
from sumagent_b.incremental import plan_views
from sumagent_b.load_stage_a import load_stage_a
from sumagent_b.logging import RunLogger
from sumagent_b.module_tree import build_module_tree


def test_views_selection_and_rendering(tmp_path: Path) -> None:
    summary_dir = Path(__file__).parent / "fixtures" / "sample_summary_a"
    stage_a = load_stage_a(summary_dir)

    selections = select_files_for_aspects(stage_a.file_summaries)

    security_files = {item["relative_path"] for item in selections["security_auth"]}
    deploy_files = {item["relative_path"] for item in selections["deploy_config"]}
    business_files = {item["relative_path"] for item in selections["business_logic"]}

    assert "src/auth.py" in security_files
    assert "config/docker.yaml" in deploy_files
    assert "src/service.py" in business_files

    view_plans = plan_views(
        [
            {"id": "security_auth"},
            {"id": "deploy_config"},
            {"id": "business_logic"},
        ],
        selections,
        {},
    )

    run_logger = RunLogger(out_dir=tmp_path)
    results = generate_views(
        selected_by_aspect=selections,
        view_plans=view_plans,
        out_dir=tmp_path,
        llm_client=None,
        run_logger=run_logger,
        dry_run=False,
    )

    for result in results.values():
        content = result.path.read_text(encoding="utf-8")
        assert "## key_files" in content

    module_tree = build_module_tree(stage_a.index.files.keys())
    overview_path = generate_project_overview(
        module_tree=module_tree,
        module_results={},
        file_summaries=stage_a.file_summaries,
        out_dir=tmp_path,
        llm_client=None,
        dry_run=False,
    )
    overview = overview_path.read_text(encoding="utf-8")
    assert "## key_files" in overview
