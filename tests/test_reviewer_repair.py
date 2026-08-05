from __future__ import annotations

from target_agent.contracts import (
    CoverageStatus, TaskContext, TaskSpec, ToolCapability, ToolResult, ToolStatus,
)
from target_agent.repair import repair_transient_connector_failures
from target_agent.reviewer import Reviewer
from target_agent.settings import Settings
from target_agent.store import EvidenceStore
from target_agent.tools.base import ScientificTool, ToolContext, ToolExecution, ToolRegistry


class RecoveringLiteratureConnector(ScientificTool):
    name = "europe_pmc_rag"
    version = "test"

    def __init__(self):
        self.calls = 0

    def run(self, context: ToolContext) -> ToolExecution:
        self.calls += 1
        return ToolExecution(result=ToolResult(
            tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED,
            context_match_score=1.0, outputs={"retried": True},
            capability=ToolCapability(validation_scope="repair test connector"),
        ), evidence=[])


def failed_result() -> ToolResult:
    return ToolResult(
        tool_name="europe_pmc_rag", tool_version="test",
        status=ToolStatus.FAILED, coverage_status=CoverageStatus.UNKNOWN,
        context_match_score=0.0, error="synthetic transient network error",
        capability=ToolCapability(validation_scope="repair test connector"),
    )


def task() -> TaskSpec:
    return TaskSpec(
        task_type="disease_to_target", question="Find traceable disease targets",
        context=TaskContext(disease="test disease"),
    )


def settings(tmp_path, *, cache_only=False) -> Settings:
    return Settings(
        _env_file=None, STEP_API_KEY=None,
        TARGET_AGENT_RUN_DIR=tmp_path / "runs",
        TARGET_AGENT_CACHE_DIR=tmp_path / "cache",
        RESEARCH_AGENT_PROJECT_DIR=tmp_path / "projects",
        TARGET_AGENT_CACHE_ONLY=cache_only,
    )


def test_reviewer_retries_failed_read_only_connector_and_rechecks_latest_attempt(tmp_path):
    spec = task()
    store = EvidenceStore(tmp_path / "run")
    initial = failed_result()
    store.add_tool_result(initial)
    reviewer = Reviewer()
    initial_findings = reviewer.review(spec, [initial], [])
    connector = RecoveringLiteratureConnector()
    traces = []

    outcome = repair_transient_connector_failures(
        task=spec, run_id="run-test", store=store,
        registry=ToolRegistry([connector]), reviewer=reviewer,
        cache_dir=tmp_path / "cache", settings=settings(tmp_path),
        results=[initial], evidence=[], findings=initial_findings,
        candidate_genes=[], tool_calls=1,
        merge_candidates=lambda current, result, limit: current,
        trace=lambda event, state, detail, related: traces.append((event, state, detail, related)),
    )

    assert connector.calls == 1
    assert len(store.tool_results()) == 2
    assert outcome.results[-1].status == ToolStatus.SUCCESS
    assert outcome.actions == [{
        "round": 1,
        "action": "retry_failed_read_only_connectors",
        "tools": ["europe_pmc_rag"],
        "outcomes": {"europe_pmc_rag": "success"},
    }]
    assert not any(row.category == "tool_failure" for row in outcome.findings)
    assert any(event == "replan" and state == "reviewer_repair" for event, state, _, _ in traces)


def test_cache_only_mode_never_retries_missing_connector_cache(tmp_path):
    spec = task()
    store = EvidenceStore(tmp_path / "run")
    initial = failed_result()
    store.add_tool_result(initial)
    connector = RecoveringLiteratureConnector()

    outcome = repair_transient_connector_failures(
        task=spec, run_id="run-test", store=store,
        registry=ToolRegistry([connector]), reviewer=Reviewer(),
        cache_dir=tmp_path / "cache", settings=settings(tmp_path, cache_only=True),
        results=[initial], evidence=[], findings=[], candidate_genes=[], tool_calls=1,
        merge_candidates=lambda current, result, limit: current,
        trace=lambda *args: None,
    )

    assert connector.calls == 0
    assert not outcome.actions
    assert len(store.tool_results()) == 1
