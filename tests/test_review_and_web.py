import json

from target_agent.contracts import (
    CoverageStatus, TaskContext, TaskSpec, ToolCapability, ToolResult, ToolStatus,
)
from target_agent.reviewer import Reviewer
from target_agent.webapp import create_app

from .test_runtime import fake_runtime, uc_task


def test_covered_false_is_blocking():
    task = TaskSpec(task_type="disease_to_target", question="Find targets", context=TaskContext(disease="Crohn disease"))
    result = ToolResult(
        tool_name="uc_omics_snapshot", tool_version="2", status=ToolStatus.OUT_OF_SCOPE,
        coverage_status=CoverageStatus.NOT_COVERED, context_match_score=0,
        outputs={"covered": False}, capability=ToolCapability(),
    )
    findings = Reviewer().review(task, [result], [])
    assert any(f.severity == "blocking" and f.category == "coverage_gap" for f in findings)


def test_api_artifact_matches_backend_without_new_numbers(tmp_path):
    runtime = fake_runtime(tmp_path)
    runtime.run(uc_task(), run_id="run-web")
    client = create_app(runtime).test_client()
    response = client.get("/api/runs/run-web/artifacts/report.json")
    assert response.status_code == 200
    report = response.get_json()
    ranking = json.loads((tmp_path / "runs" / "run-web" / "ranked_targets.json").read_text())
    assert report["ranked_targets"] == ranking

