import json

import pytest
from pydantic import ValidationError

from target_agent.contracts import (
    CaseRecord, CoverageStatus, ExecutionPlan, PlanStep, TaskContext, TaskSpec,
    TerminalStatus, ToolCapability, ToolResult, ToolStatus,
)
from target_agent.legacy import adapt_evidence, reject_mixed_versions
from target_agent.schema_export import MODELS, export_schemas


def task() -> TaskSpec:
    return TaskSpec(task_type="disease_to_target", question="Find targets", context=TaskContext(disease="ulcerative colitis"))


def test_not_covered_cannot_be_success():
    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="bad", tool_version="1", status=ToolStatus.SUCCESS,
            coverage_status=CoverageStatus.NOT_COVERED, context_match_score=0,
            capability=ToolCapability(),
        )


def test_legacy_requires_tool_run_id():
    with pytest.raises(ValueError, match="tool_run_id"):
        adapt_evidence({
            "contract_version": "1.1.0", "evidence_class": "literature",
            "claim": "claim", "source_uri": "https://example.org",
        })


def test_mixed_versions_rejected():
    with pytest.raises(ValueError, match="mixed"):
        reject_mixed_versions([{"contract_version": "1.1.0"}, {"contract_version": "2.0.0"}])


def test_schema_export_is_pydantic_canonical(tmp_path):
    (tmp_path / "stale.schema.json").write_text("{}")
    paths = export_schemas(tmp_path)
    assert len(paths) == len(MODELS)
    assert not (tmp_path / "stale.schema.json").exists()
    task_schema = json.loads((tmp_path / "task_spec.schema.json").read_text())
    assert task_schema["properties"]["contract_version"]["const"] == "2.0.0"


def test_case_cannot_promote_without_scientific_approval():
    spec = task()
    plan = ExecutionPlan(task_id=spec.task_id, planner_backend="test", steps=[PlanStep(step_id="x", name="x")])
    with pytest.raises(ValidationError):
        CaseRecord(
            run_id="run-test", task_spec=spec, plan=plan, tool_run_ids=[], finding_ids=[], revision_history=[],
            final_status=TerminalStatus.COMPLETED, final_claim_ids=[], scientific_review="pending", promotion_eligible=True,
        )
