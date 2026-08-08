"""Parity tests: LangGraph runtime must reproduce the legacy runtime's observable behavior.

Both runtimes share the same fake registry and deterministic fallback planner, so any
difference in terminal status, ranking, trace topology or checkpoint/resume behavior
indicates a migration regression rather than a scientific difference.
"""
import json

from target_agent.contracts import TaskConstraints, TaskContext, TaskSpec
from target_agent.planner import Planner
from target_agent.runtime import TargetDiscoveryRuntime
from target_agent.runtime_langgraph import LangGraphRuntime
from target_agent.tools.base import ToolRegistry

from .fakes import FakeGenericOmics, FakeLiterature, FakeOpenTargets


def make_runtime(cls, tmp_path):
    return cls(
        runs_dir=tmp_path / "runs", cache_dir=tmp_path / "cache", planner=Planner(None),
        registry=ToolRegistry([
            FakeGenericOmics(), FakeOpenTargets(), FakeLiterature(),
        ]),
    )


def uc_task(**overrides):
    payload = dict(
        task_id="task-test-uc", task_type="disease_to_target", question="Find traceable UC targets",
        context=TaskContext(disease="ulcerative colitis", disease_id="MONDO_0005101", tissue="rectum",
                            cell_type="T cell", desired_phenotype="restore state"),
    )
    payload.update(overrides)
    return TaskSpec(**payload)


def _jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def observable(run_dir):
    """Extract everything a downstream consumer can observe from a run directory."""
    evidence = _jsonl(run_dir / "evidence_items.jsonl")
    findings = _jsonl(run_dir / "reviewer_findings.jsonl")
    trace = _jsonl(run_dir / "trace.jsonl")
    tool_results = _jsonl(run_dir / "tool_results.jsonl")
    ranking = json.loads((run_dir / "ranked_targets.json").read_text())
    status = json.loads((run_dir / "status.json").read_text())
    return {
        "terminal_status": status["terminal_status"],
        "status_state": status["state"],
        "ranking": [(row["gene"], row["scores"], row["decision"]) for row in ranking],
        "evidence": sorted((item["gene_symbol"], item["statement"], item["source_span"]) for item in evidence),
        "findings": sorted((f["category"], f["severity"]) for f in findings),
        "tool_results": [(r["tool_name"], r["status"], r["coverage_status"]) for r in tool_results],
        "trace_topology": [(event["event_type"], event["state"]) for event in trace],
        "checkpoint_stage": json.loads((run_dir / "checkpoint.json").read_text())["stage"],
        "report_exists": (run_dir / "report.md").exists(),
        "case_exists": (run_dir / "case_record.json").exists(),
    }


def test_langgraph_matches_legacy_runtime_on_uc_pipeline(tmp_path):
    legacy = make_runtime(TargetDiscoveryRuntime, tmp_path / "legacy")
    graph = make_runtime(LangGraphRuntime, tmp_path / "graph")
    legacy_status = legacy.run(uc_task(), run_id="run-parity")
    graph_status = graph.run(uc_task(), run_id="run-parity")
    assert legacy_status["terminal_status"] == graph_status["terminal_status"] == "completed"
    assert observable(tmp_path / "legacy" / "runs" / "run-parity") == observable(tmp_path / "graph" / "runs" / "run-parity")


def test_langgraph_matches_legacy_under_tool_call_budget(tmp_path):
    task = uc_task(constraints=TaskConstraints(max_tool_calls=1))
    legacy = make_runtime(TargetDiscoveryRuntime, tmp_path / "legacy")
    graph = make_runtime(LangGraphRuntime, tmp_path / "graph")
    legacy.run(task, run_id="run-budget")
    graph.run(task, run_id="run-budget")
    left = observable(tmp_path / "legacy" / "runs" / "run-budget")
    right = observable(tmp_path / "graph" / "runs" / "run-budget")
    assert left == right
    assert left["terminal_status"] == "completed_with_gaps"
    assert ("coverage_gap", "major") in left["findings"]
    assert ("degradation", "tool_execution") in left["trace_topology"]


def test_langgraph_resume_terminal_run_is_idempotent(tmp_path):
    runtime = make_runtime(LangGraphRuntime, tmp_path)
    first = runtime.run(uc_task(), run_id="run-resume")
    before = (tmp_path / "runs" / "run-resume" / "trace.jsonl").read_text()
    second = runtime.run(uc_task(), run_id="run-resume", resume=True)
    after = (tmp_path / "runs" / "run-resume" / "trace.jsonl").read_text()
    assert first == second
    assert before == after


def test_trace_observer_runs_only_after_authoritative_trace_is_durable(tmp_path):
    run_dir = tmp_path / "runs" / "run-observer"
    observed = []

    def observer(event):
        durable_ids = {row["event_id"] for row in _jsonl(run_dir / "trace.jsonl")}
        assert event.event_id in durable_ids
        observed.append(event.event_id)

    runtime = LangGraphRuntime(
        runs_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        planner=Planner(None),
        registry=ToolRegistry([FakeGenericOmics(), FakeOpenTargets(), FakeLiterature()]),
        trace_observer=observer,
    )
    runtime.run(uc_task(), run_id="run-observer")

    assert observed == [row["event_id"] for row in _jsonl(run_dir / "trace.jsonl")]
    assert runtime.trace_observer_errors == []


def test_trace_observer_failure_does_not_change_scientific_terminal_status(tmp_path):
    runtime = LangGraphRuntime(
        runs_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        planner=Planner(None),
        registry=ToolRegistry([FakeGenericOmics(), FakeOpenTargets(), FakeLiterature()]),
        trace_observer=lambda event: (_ for _ in ()).throw(RuntimeError("projection unavailable")),
    )

    status = runtime.run(uc_task(), run_id="run-observer-failure")

    assert status["terminal_status"] == "completed"
    assert runtime.trace_observer_errors


def test_langgraph_resume_mid_pipeline_matches_legacy_fresh_run(tmp_path):
    """A crashed mid-pipeline LangGraph run, resumed, must match a fresh legacy run."""
    legacy = make_runtime(TargetDiscoveryRuntime, tmp_path / "legacy")
    legacy_status = legacy.run(uc_task(), run_id="run-fresh")

    # simulate a crash: run only far enough to persist the task, then resume
    from target_agent.store import EvidenceStore
    run_dir = tmp_path / "graph" / "runs" / "run-crashed"
    store = EvidenceStore(run_dir)
    store.save_task(uc_task())
    store.checkpoint({"stage": "intake", "completed_steps": [], "candidate_genes": [], "tool_calls": 0})

    graph = make_runtime(LangGraphRuntime, tmp_path / "graph")
    graph_status = graph.run(uc_task(), run_id="run-crashed", resume=True)
    assert graph_status["terminal_status"] == legacy_status["terminal_status"] == "completed"
    left = observable(tmp_path / "legacy" / "runs" / "run-fresh")
    right = observable(tmp_path / "graph" / "runs" / "run-crashed")
    # resume adds one extra intake trace; compare everything else
    assert {key: value for key, value in left.items() if key != "trace_topology"} == \
           {key: value for key, value in right.items() if key != "trace_topology"}


class HintedPlanner:
    """Deterministic planner wrapper that reports pattern/paper hints like the Step planner."""

    def __init__(self, base):
        self._base = base
        self.registry = base.registry
        self.last_pattern_hints = [{"pattern_id": "pattern-1"}]
        self.last_paper_evidence = [{"chunk_id": "chunk-1", "pmid": "12345"}]

    def create_plan(self, task):
        return self._base.create_plan(task)


def test_langgraph_trace_records_pattern_and_paper_hints(tmp_path):
    runtime = LangGraphRuntime(
        runs_dir=tmp_path / "runs", cache_dir=tmp_path / "cache",
        planner=HintedPlanner(Planner(None)),
        registry=ToolRegistry([FakeGenericOmics(), FakeOpenTargets(), FakeLiterature()]),
    )
    status = runtime.run(uc_task(), run_id="run-hints")
    assert status["terminal_status"] == "completed"
    trace = _jsonl(tmp_path / "runs" / "run-hints" / "trace.jsonl")
    types = [event["event_type"] for event in trace]
    assert "planner_pattern_hints" in types
    assert "planner_paper_evidence" in types
    pattern_event = next(event for event in trace if event["event_type"] == "planner_pattern_hints")
    assert pattern_event["detail"]["pattern_ids"] == ["pattern-1"]
