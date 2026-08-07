import json
from pathlib import Path

from target_agent.contracts import (
    ArtifactRef, CoverageStatus, TaskContext, TaskSpec, TerminalStatus, ToolCapability,
    ToolResult, ToolStatus,
)
from target_agent.reporting import build_disease_report
from target_agent.reviewer import Reviewer
from target_agent.webapp import _build_public_bundle, create_app

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
    assert capabilities.get_json()["contract_version"] == "2.2.0"


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


def test_public_bundle_preserves_legacy_source_contract_version():
    bundle = _build_public_bundle(
        "run-legacy", {"contract_version": "2.1.0"},
        {"contract_version": "2.1.0"}, {}, [], [], [], [],
    )
    assert bundle["contract_version"] == "2.1.0"
    assert bundle["source_contract_version"] == "2.1.0"
    assert bundle["rendered_contract_version"] == "2.2.0"


def test_genetics_report_preserves_stage_artifact_provenance():
    stage_outputs = {
        "genetics_input_audit": {"assets": [{"asset_id": "gwas-1"}]},
        "fine_mapping_audit": {"credible_sets": [{"signal_id": "signal-1"}]},
        "eqtl_colocalization_audit": {"colocalizations": [{"gene_symbol": "GENE1"}]},
        "genetics_candidate_extraction": {"locus_to_gene_links": [{"gene_symbol": "GENE1"}]},
    }
    results = [
        ToolResult(
            tool_run_id=f"tool-{index}", tool_name=tool_name, tool_version="1",
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED,
            context_match_score=1.0, outputs=outputs, capability=ToolCapability(),
            artifacts=[ArtifactRef(
                name=f"{tool_name}.json", uri=f"artifact://{tool_name}.json",
                sha256=str(index) * 64, media_type="application/json",
            )],
        )
        for index, (tool_name, outputs) in enumerate(stage_outputs.items(), start=1)
    ]

    report, _ = build_disease_report(
        TaskSpec(
            task_type="disease_to_target", question="Find targets",
            context=TaskContext(disease="example disease"),
        ),
        TerminalStatus.COMPLETED, [], [], [], results,
    )

    trace = report["genetics_selection_trace"]
    assert trace["input_audit"] == [{"asset_id": "gwas-1"}]
    assert trace["credible_sets"] == [{"signal_id": "signal-1"}]
    assert trace["colocalizations"] == [{"gene_symbol": "GENE1"}]
    assert trace["locus_to_gene_links"] == [{"gene_symbol": "GENE1"}]
    for index, tool_name in enumerate(stage_outputs, start=1):
        provenance = trace["provenance"][tool_name][0]
        artifact_name = f"{tool_name}.json"
        assert trace["selected_tool_runs"][tool_name] == f"tool-{index}"
        assert provenance["tool_run_id"] == f"tool-{index}"
        assert provenance["artifacts"][0]["name"] == artifact_name
        assert provenance["artifact_checksums"][artifact_name] == str(index) * 64


def test_missing_run_event_stream_and_invalid_json_fail_fast(tmp_path):
    client = create_app(fake_runtime(tmp_path)).test_client()
    assert client.get("/api/runs/run-does-not-exist/events").status_code == 404
    response = client.post("/api/runs", data="not-json", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be a JSON object"


def test_web_accepts_homogeneous_2_1_task_through_explicit_adapter(tmp_path):
    client = create_app(fake_runtime(tmp_path)).test_client()
    response = client.post("/api/runs", json={
        "contract_version": "2.1.0",
        "task_type": "disease_to_target",
        "question": "Find traceable UC targets",
        "context": {
            "contract_version": "2.1.0",
            "disease": "ulcerative colitis",
        },
        "constraints": {"contract_version": "2.1.0"},
    })
    assert response.status_code == 202
    assert response.get_json()["run_id"].startswith("run-")


def test_workbench_assets_are_utf8_chinese_and_demo_oriented():
    static = Path(__file__).resolve().parents[1] / "src" / "target_agent" / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "app.js").read_text(encoding="utf-8")
    combined = html + script
    assert "科研工作台" in html
    assert "新建项目" in html
    assert "/api/projects" in script
    assert "/forks" in script
    assert "proposeFork" in script
    assert "decideFork" in script
    assert "accept_checkpoint" in script
    assert chr(0xFFFD) not in combined
    assert "读取" not in combined
