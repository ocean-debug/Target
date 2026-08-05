from __future__ import annotations

import json
from collections import Counter
from types import SimpleNamespace

from target_agent.contracts import TaskContext, TaskSpec, ToolDescriptor, TraceEvent
from target_agent.research_contracts import (
    AutonomyMode, DecisionAction, DecisionEvent, ProjectState, ProjectStatus,
    ResearchGoal,
    ResearchProjectSpec,
    WorkItemResult,
    WorkItemStatus,
)
from target_agent.research_modules import (
    ModuleDescriptor,
    ModuleExecution,
    PendingArtifact,
    ResearchModuleRegistry,
    default_research_registry,
)
from target_agent.research_planner import ResearchPlanner
from target_agent.research_runtime import ResearchProjectRuntime
from target_agent.research_store import ResearchProjectStore
from target_agent.store import EvidenceStore
from target_agent.settings import Settings


BASELINE_MODULES = (
    "project_brief",
    "literature_search",
    "hypothesis_generation",
    "independent_review",
    "research_report",
)


def research_project(
    project_id: str = "project-runtime",
    *,
    domain: str = "life_science",
    context: dict | None = None,
    autonomy_mode: AutonomyMode = AutonomyMode.AUTONOMOUS,
) -> ResearchProjectSpec:
    return ResearchProjectSpec(
        project_id=project_id,
        title="Traceable disease mechanism project",
        domain=domain,
        goal=ResearchGoal(
            question="Which disease mechanisms and targets are supported by public evidence?",
            success_criteria=["Every released conclusion is traceable to a durable artifact."],
            deliverables=["A reviewed research report with explicit evidence gaps."],
        ),
        context=context or {},
        autonomy_mode=autonomy_mode,
    )


class FakeResearchModule:
    """Deterministic module used to exercise orchestration, never a network adapter."""

    def __init__(
        self,
        name: str,
        calls: Counter,
        *,
        fail_module: str | None = None,
        bad_contract_module: str | None = None,
    ):
        self.descriptor = ModuleDescriptor(
            name=name,
            description=f"Deterministic fake module for {name}",
            input_types=("object",),
            output_types=("object",),
            execution_policy="deterministic_test",
        )
        self.calls = calls
        self.fail_module = fail_module
        self.bad_contract_module = bad_contract_module

    def execute(self, context):
        name = self.descriptor.name
        self.calls[name] += 1
        if name == self.fail_module:
            raise RuntimeError("synthetic module failure")

        if name == "project_brief":
            outputs = {
                "question": context.project.goal.question,
                "deliverables": context.project.goal.deliverables,
                "success_criteria": context.project.goal.success_criteria,
            }
            status = WorkItemStatus.COMPLETED
        elif name == "literature_search":
            outputs = {
                "query": context.project.goal.question,
                "record_count": 1,
                "source_ids": ["PMID:FAKE-1"],
                "retrieval_hits_are_claims": False,
            }
            status = WorkItemStatus.COMPLETED
        elif name == "hypothesis_generation":
            outputs = {
                "hypothesis_count": 1,
                "hypotheses": [{
                    "statement": "A falsifiable test hypothesis",
                    "source_ids": ["PMID:FAKE-1"],
                    "falsification_test": "Reject if the prespecified perturbation has no effect.",
                }],
            }
            status = WorkItemStatus.COMPLETED
        elif name == "target_discovery":
            if "target_task_spec" not in context.project.context:
                return ModuleExecution(result=WorkItemResult(
                    item_id=context.item.item_id,
                    module=name,
                    status=WorkItemStatus.NEEDS_INPUT,
                    summary="A target_task_spec is required for the vertical workflow.",
                    limitations=["No disease-target input contract was supplied."],
                ))
            outputs = {
                "child_run_id": "run-fake-target", "terminal_status": "completed",
                "ranked_target_count": 10, "target_card_count": 5,
                "experiment_plan_count": 5, "deliverables_complete": True,
                "domain_activity_projection_complete": True,
            }
            status = WorkItemStatus.COMPLETED
        elif name == "independent_review":
            blocking = [
                item_id for item_id, result in context.prior_results.items()
                if result.status in {WorkItemStatus.FAILED, WorkItemStatus.NEEDS_INPUT}
            ]
            outputs = {"assessment_count": len(context.prior_results), "blocking_failures": blocking}
            status = WorkItemStatus.COMPLETED_WITH_GAPS if blocking else WorkItemStatus.COMPLETED
        elif name == "research_report":
            gaps = [
                item_id for item_id, result in context.prior_results.items()
                if result.status != WorkItemStatus.COMPLETED
            ]
            outputs = {"reported_items": len(context.prior_results), "gap_count": len(gaps)}
            status = WorkItemStatus.COMPLETED_WITH_GAPS if gaps else WorkItemStatus.COMPLETED
        else:  # pragma: no cover - registry construction fixes the module set
            raise AssertionError(f"unexpected fake module {name}")

        if name == self.bad_contract_module:
            outputs = {"wrong_field": True}

        suffix = ".md" if name == "research_report" else ".json"
        artifact_path = context.output_dir / f"{name}{suffix}"
        if suffix == ".md":
            artifact_path.write_text(
                "# Fake research report\n\nAll content comes from typed fake results.\n",
                encoding="utf-8",
            )
            media_type = "text/markdown"
        else:
            artifact_path.write_text(json.dumps(outputs, ensure_ascii=False), encoding="utf-8")
            media_type = "application/json"
        logical_name = "research_report" if name == "research_report" else f"{name}_output"
        return ModuleExecution(
            result=WorkItemResult(
                item_id=context.item.item_id,
                module=name,
                status=status,
                summary=f"Fake {name} completed.",
                outputs=outputs,
            ),
            artifacts=[PendingArtifact(artifact_path, logical_name, media_type)],
        )


def fake_research_runtime(
    tmp_path,
    *,
    fail_module: str | None = None,
    bad_contract_module: str | None = None,
):
    calls: Counter = Counter()
    modules = [
        FakeResearchModule(
            name,
            calls,
            fail_module=fail_module,
            bad_contract_module=bad_contract_module,
        )
        for name in (*BASELINE_MODULES, "target_discovery")
    ]
    registry = ResearchModuleRegistry(modules)
    settings = Settings(
        _env_file=None,
        STEP_API_KEY=None,
        TARGET_AGENT_RUN_DIR=tmp_path / "runs",
        RESEARCH_AGENT_PROJECT_DIR=tmp_path / "projects",
        TARGET_AGENT_CACHE_DIR=tmp_path / "cache",
        TARGET_AGENT_CACHE_ONLY=True,
        TARGET_AGENT_WEB_WORKERS=1,
        TARGET_AGENT_WEB_QUEUE_SIZE=2,
    )
    runtime = ResearchProjectRuntime(
        projects_dir=settings.projects_dir,
        cache_dir=settings.cache_dir,
        registry=registry,
        planner=ResearchPlanner(registry, client=None),
        settings=settings,
    )
    return runtime, calls


def test_langgraph_project_runs_end_to_end_and_persists_report(tmp_path):
    runtime, calls = fake_research_runtime(tmp_path)
    project = research_project()

    terminal = runtime.run(project)

    assert terminal["status"] == ProjectStatus.COMPLETED.value
    assert calls == Counter({name: 1 for name in BASELINE_MODULES})
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    assert [event.sequence for event in store.read_events()] == list(range(1, len(store.read_events()) + 1))
    assert set(store.load_work_item_results()) == set(BASELINE_MODULES)
    report = next(row for row in store.read_artifacts() if row.logical_name == "research_report")
    assert store.artifact_path(report).read_text(encoding="utf-8").startswith("# Fake research report")
    assert store.read_decisions()[-1].action.value == "release"


def test_output_contract_failure_degrades_release_and_is_a_blocking_assessment(tmp_path):
    runtime, _ = fake_research_runtime(tmp_path, bad_contract_module="literature_search")
    project = research_project("project-contract-gap")

    terminal = runtime.run(project)

    assert terminal["status"] == ProjectStatus.COMPLETED_WITH_GAPS.value
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    literature = store.load_work_item_results()["literature_search"]
    assert literature.status == WorkItemStatus.COMPLETED_WITH_GAPS
    assert any("missing required output" in limitation for limitation in literature.limitations)
    assert any(
        assessment.target_id == "literature_search"
        and assessment.dimension.value == "schema_alignment"
        and assessment.result.value == "fail"
        and assessment.blocking
        for assessment in store.read_assessments()
    )


def test_module_exception_still_produces_a_durable_gap_report(tmp_path):
    runtime, calls = fake_research_runtime(tmp_path, fail_module="literature_search")
    project = research_project("project-module-failure")

    terminal = runtime.run(project)

    assert terminal["status"] == ProjectStatus.COMPLETED_WITH_GAPS.value
    assert calls["research_report"] == 1
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    assert store.load_work_item_results()["literature_search"].status == WorkItemStatus.FAILED
    report_result = store.load_work_item_results()["research_report"]
    assert report_result.status == WorkItemStatus.COMPLETED_WITH_GAPS
    assert report_result.outputs["gap_count"] >= 1
    assert any(row.logical_name == "research_report" for row in store.read_artifacts())


def test_resume_of_terminal_project_is_idempotent_and_does_not_rerun_modules(tmp_path):
    runtime, calls = fake_research_runtime(tmp_path)
    project = research_project("project-resume")
    first = runtime.run(project)
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    events_before = [row.model_dump(mode="json") for row in store.read_events()]
    calls_before = calls.copy()

    second = runtime.run(project, resume=True)

    assert second == first
    assert calls == calls_before
    assert [row.model_dump(mode="json") for row in store.read_events()] == events_before


def test_vertical_project_without_target_spec_fails_closed_with_reported_gap(tmp_path):
    runtime, calls = fake_research_runtime(tmp_path)
    project = research_project("project-vertical-missing", domain="disease_target_discovery")

    terminal = runtime.run(project)

    assert terminal["status"] == ProjectStatus.NEEDS_INPUT.value
    assert calls["target_discovery"] == 0
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    target = store.load_work_item_results()["target_discovery"]
    assert target.status == WorkItemStatus.NEEDS_INPUT
    assert any("target_task_spec" in limitation for limitation in target.limitations)
    assert store.load_work_item_results()["research_report"].status == WorkItemStatus.COMPLETED_WITH_GAPS


def test_checkpointed_project_requires_plan_and_release_acceptance(tmp_path):
    runtime, calls = fake_research_runtime(tmp_path)
    project = research_project(
        "project-checkpointed", autonomy_mode=AutonomyMode.CHECKPOINTED,
    )

    first = runtime.run(project)
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    plan = store.load_plan()
    assert first["status"] == ProjectStatus.NEEDS_INPUT.value
    assert not calls

    store.append_decision(DecisionEvent(
        project_id=project.project_id, action=DecisionAction.ACCEPT,
        target_ids=[plan.plan_id], actor="test-reviewer", rationale="Plan is in scope.",
    ))
    second = runtime.run(project, resume=True)
    assert second["status"] == ProjectStatus.WAITING_REVIEW.value
    assert calls["research_report"] == 1

    store.append_decision(DecisionEvent(
        project_id=project.project_id, action=DecisionAction.ACCEPT,
        target_ids=[f"release:{plan.plan_id}"], actor="test-reviewer",
        rationale="Release artifacts passed review.", reversible=False,
    ))
    third = runtime.run(project, resume=True)
    assert third["status"] == ProjectStatus.COMPLETED.value


def _target_project(project_id: str) -> ResearchProjectSpec:
    task = TaskSpec(
        task_type="disease_to_target",
        question="Which targets should be prioritized?",
        context=TaskContext(disease="lung adenocarcinoma", tissue="lung"),
    )
    return research_project(
        project_id,
        domain="disease_target_discovery",
        context={"target_task_spec": task.model_dump(mode="json")},
    )


def _real_target_project_runtime(tmp_path):
    settings = Settings(
        _env_file=None,
        STEP_API_KEY=None,
        TARGET_AGENT_RUN_DIR=tmp_path / "runs",
        RESEARCH_AGENT_PROJECT_DIR=tmp_path / "projects",
        TARGET_AGENT_CACHE_DIR=tmp_path / "cache",
        TARGET_AGENT_CACHE_ONLY=True,
    )
    registry = default_research_registry(settings)
    runtime = ResearchProjectRuntime(
        projects_dir=settings.projects_dir,
        cache_dir=settings.cache_dir,
        registry=registry,
        planner=ResearchPlanner(registry, client=None),
        settings=settings,
    )
    return runtime


def test_child_runtime_exception_preserves_trace_artifact_and_gap_report(tmp_path, monkeypatch):
    class CrashingChildRuntime:
        def __init__(self, *, runs_dir, cache_dir, settings, trace_observer):
            self.runs_dir = runs_dir
            self.trace_observer = trace_observer
            self.trace_observer_errors = []
            self.registry = SimpleNamespace(descriptors=[ToolDescriptor(
                tool_id="geo_search", evidence_dimension="dataset_discovery",
                description="GEO search connector.",
            )])

        def run(self, task, run_id, resume=False):
            store = EvidenceStore(self.runs_dir / run_id)
            event = TraceEvent(
                run_id=run_id, task_id=task.task_id, event_type="tool_call",
                state="tool_execution", detail={"tool": "geo_search", "step_id": "geo"},
            )
            store.add_trace(event)
            self.trace_observer(event)
            raise RuntimeError("synthetic child interruption")

    monkeypatch.setattr("target_agent.runtime_langgraph.LangGraphRuntime", CrashingChildRuntime)
    runtime = _real_target_project_runtime(tmp_path)
    project = _target_project("project-child-error")

    terminal = runtime.run(project)

    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    assert terminal["status"] == ProjectStatus.COMPLETED_WITH_GAPS.value
    assert store.load_work_item_results()["target_discovery"].error == "RuntimeError"
    assert len(store.read_domain_activities()) == 1
    assert any(row.logical_name == "target_discovery_trace" for row in store.read_artifacts())
    assert any(row.logical_name == "research_report" for row in store.read_artifacts())
    store.assert_integrity()


def test_interrupted_first_attempt_resumes_once_and_backfills_without_duplicates(tmp_path, monkeypatch):
    class TerminalChildRuntime:
        def __init__(self, *, runs_dir, cache_dir, settings, trace_observer):
            self.runs_dir = runs_dir
            self.trace_observer = trace_observer
            self.trace_observer_errors = []
            self.registry = SimpleNamespace(descriptors=[ToolDescriptor(
                tool_id="open_targets", evidence_dimension="multi_evidence",
                description="Open Targets connector.",
            )])

        def run(self, task, run_id, resume=False):
            assert resume is True
            return {"terminal_status": "completed"}

    monkeypatch.setattr("target_agent.runtime_langgraph.LangGraphRuntime", TerminalChildRuntime)
    runtime = _real_target_project_runtime(tmp_path)
    project = _target_project("project-child-resume")
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    store.create(project)
    plan = runtime.planner.deterministic(project)
    store.save_plan(plan)
    store.save_state(ProjectState(
        project_id=project.project_id,
        status=ProjectStatus.RUNNING,
        attempts={"target_discovery": 1},
    ))
    child_run_id = f"target-{project.project_id}"
    child_dir = store.project_dir / "domain_runs" / child_run_id
    child_store = EvidenceStore(child_dir)
    event = TraceEvent(
        run_id=child_run_id,
        task_id=project.context["target_task_spec"]["task_id"],
        event_type="tool_result",
        state="tool_execution",
        detail={
            "tool": "open_targets", "status": "success",
            "coverage_status": "covered", "context_match_score": 0.8,
        },
    )
    child_store.add_trace(event)
    (child_dir / "report.md").write_text("# Child report\n", encoding="utf-8")
    (child_dir / "ranked_targets.json").write_text('[{"gene":"GENE1"}]\n', encoding="utf-8")
    (child_dir / "target_cards.json").write_text(
        '[{"gene_symbol":"GENE1","experiment_plan":{"hypothesis":"test"}}]\n',
        encoding="utf-8",
    )

    terminal = runtime.run(project, resume=True)

    assert terminal["status"] == ProjectStatus.COMPLETED.value
    state = store.load_state()
    assert state.attempts["target_discovery"] == 2
    assert [row.source_trace_id for row in store.read_domain_activities()] == [event.event_id]
    assert len([row for row in store.read_artifacts() if row.logical_name == "target_discovery_trace"]) == 1
    store.assert_integrity()
