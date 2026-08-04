import json
from pathlib import Path

from target_agent.contracts import (
    CoverageStatus, TaskContext, TaskSpec, ToolCapability, ToolResult, ToolStatus,
)
from target_agent.reviewer import Reviewer
from target_agent.webapp import create_app

from .test_runtime import fake_runtime, uc_task


def test_missing_generic_omics_is_a_gap_not_a_refusal():
    task = TaskSpec(task_type="disease_to_target", question="Find targets", context=TaskContext(disease="Crohn disease"))
    result = ToolResult(
        tool_name="uc_omics_snapshot", tool_version="2", status=ToolStatus.OUT_OF_SCOPE,
        coverage_status=CoverageStatus.NOT_COVERED, context_match_score=0,
        outputs={"covered": False}, capability=ToolCapability(),
    )
    findings = Reviewer().review(task, [result], [])
    assert any(f.severity == "major" and f.category == "coverage_gap" for f in findings)


def test_api_artifact_matches_backend_without_new_numbers(tmp_path):
    runtime = fake_runtime(tmp_path)
    runtime.run(uc_task(), run_id="run-web")
    client = create_app(runtime).test_client()
    response = client.get("/api/runs/run-web/artifacts/report.json")
    assert response.status_code == 200
    report = response.get_json()
    ranking = json.loads((tmp_path / "runs" / "run-web" / "ranked_targets.json").read_text())
    assert report["ranked_targets"] == ranking


def test_health_and_capabilities_never_expose_secret(tmp_path):
    client = create_app(fake_runtime(tmp_path)).test_client()
    health = client.get("/healthz")
    assert health.status_code == 200
    capabilities = client.get("/api/capabilities")
    assert capabilities.status_code == 200
    text = capabilities.get_data(as_text=True)
    assert "step_api_key" not in text.lower()
    assert capabilities.get_json()["contract_version"] == "2.1.0"


def test_demo_catalog_and_bundle_are_frontend_ready(tmp_path):
    runtime = fake_runtime(tmp_path)
    runtime.run(uc_task(), run_id="run-luad-v21-cached-3")
    client = create_app(runtime).test_client()

    catalog = client.get("/api/demo/cases")
    assert catalog.status_code == 200
    cases = {item["id"]: item for item in catalog.get_json()["cases"]}
    assert cases["luad"]["available"] is True
    assert cases["uc"]["available"] is False
    assert "run_id" not in cases["uc"]

    response = client.get("/api/runs/run-luad-v21-cached-3/bundle")
    assert response.status_code == 200
    bundle = response.get_json()
    assert bundle["run"]["terminal_status"] == "completed"
    assert len(bundle["plan"]["steps"]) >= 1
    assert len(bundle["ranking"]) == 10
    assert len(bundle["target_cards"]) == 5
    assert bundle["evidence"]["total"] >= 1
    assert bundle["tools"]
    assert bundle["trace"]
    assert "tool_run_id" not in json.dumps(bundle["tools"])


def test_missing_run_event_stream_and_invalid_json_fail_fast(tmp_path):
    client = create_app(fake_runtime(tmp_path)).test_client()
    assert client.get("/api/runs/run-does-not-exist/events").status_code == 404
    response = client.post("/api/runs", data="not-json", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be a JSON object"


def test_workbench_assets_are_utf8_chinese_and_demo_oriented():
    static = Path(__file__).resolve().parents[1] / "src" / "target_agent" / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "app.js").read_text(encoding="utf-8")
    combined = html + script
    assert "科研工作台" in html
    assert "已验证案例" in html
    assert "/api/demo/cases" in script
    assert "/bundle" in script
    assert "item.reasons" in script
    assert not any(marker in combined for marker in ("锛", "鍔", "鐮", "璇诲彇"))
