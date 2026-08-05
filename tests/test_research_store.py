import json

import pytest

from target_agent.contracts import ToolDescriptor, TraceEvent
from target_agent.research_contracts import (
    AssessmentDimension,
    AssessmentLevel,
    AssessmentRecord,
    AssessmentResult,
    DecisionAction,
    DecisionEvent,
    ProjectState,
    ProjectStatus,
    ResearchGoal,
    ResearchPlan,
    ResearchProjectSpec,
    WorkItemResult,
    WorkItemSpec,
    WorkItemStatus,
)
from target_agent.research_store import ProjectBusyError, ResearchProjectStore
from target_agent.research_projection import project_trace_event


def project_spec(project_id="project-test"):
    return ResearchProjectSpec(
        project_id=project_id,
        title="Traceable research project",
        goal=ResearchGoal(
            question="Which mechanism should be tested next?",
            success_criteria=["Every conclusion has a durable artifact"],
            deliverables=["Research report"],
        ),
    )


def research_plan(project_id="project-test"):
    return ResearchPlan(
        plan_id="plan-test",
        project_id=project_id,
        planner_backend="deterministic-test",
        rationale="Exercise the durable project store.",
        items=[
            WorkItemSpec(
                item_id="literature",
                title="Collect literature",
                module="literature_search",
                objective="Collect grounded source records.",
                acceptance_criteria=["At least one source is retained"],
            )
        ],
    )


def initialized_store(tmp_path):
    store = ResearchProjectStore(tmp_path / "projects", "project-test")
    store.create(project_spec())
    store.save_plan(research_plan())
    return store


def test_project_store_round_trip_and_integrity(tmp_path):
    store = initialized_store(tmp_path)
    work_file = store.project_dir / "work_items" / "literature" / "records.json"
    work_file.parent.mkdir(parents=True)
    work_file.write_text('{"pmid": "123"}\n', encoding="utf-8")
    artifact = store.register_artifact(work_file, "literature", "source-records", "application/json")

    result = WorkItemResult(
        item_id="literature",
        module="literature_search",
        status=WorkItemStatus.COMPLETED,
        summary="One source retained.",
        outputs={"record_count": 1},
        artifact_ids=[artifact.artifact_id],
        evidence_refs=["https://pubmed.ncbi.nlm.nih.gov/123/"],
    )
    store.save_work_item_result(result)
    store.save_state(ProjectState(
        project_id="project-test",
        status=ProjectStatus.COMPLETED,
        completed_items=["literature"],
        attempts={"literature": 1},
    ))
    first = store.append_event("item_started", "running", "literature")
    second = store.append_event("item_completed", "completed", "literature")
    store.append_assessment(AssessmentRecord(
        project_id="project-test",
        target_id=artifact.artifact_id,
        target_digest=artifact.sha256,
        dimension=AssessmentDimension.INTEGRITY,
        level=AssessmentLevel.A0,
        result=AssessmentResult.PASS,
        actor="research-store",
        method="sha256",
        rationale="Stored bytes match the immutable record.",
    ))
    store.append_decision(DecisionEvent(
        project_id="project-test",
        action=DecisionAction.ACCEPT,
        target_ids=[artifact.artifact_id],
        rationale="Integrity gate passed.",
        actor="test-reviewer",
    ))

    assert (store.load_spec().model_dump(mode="json", exclude={"created_at"})
            == project_spec().model_dump(mode="json", exclude={"created_at"}))
    assert (store.load_plan().model_dump(mode="json", exclude={"created_at"})
            == research_plan().model_dump(mode="json", exclude={"created_at"}))
    assert store.load_state().status == ProjectStatus.COMPLETED
    assert store.load_work_item_results()["literature"] == result
    assert [first.sequence, second.sequence] == [1, 2]
    assert store.read_assessments()[0].target_digest == artifact.sha256
    assert store.read_decisions()[0].action == DecisionAction.ACCEPT
    assert store.artifact_path(artifact).read_text(encoding="utf-8") == work_file.read_text(encoding="utf-8")
    store.assert_integrity()


def test_spec_and_plan_are_immutable_but_idempotent(tmp_path):
    store = initialized_store(tmp_path)
    store.create(project_spec())
    store.save_plan(research_plan())

    changed_spec = project_spec().model_copy(update={"title": "A different project title"})
    with pytest.raises(ValueError, match="immutable"):
        store.create(changed_spec)
    changed_plan = research_plan().model_copy(update={"rationale": "Changed after approval."})
    with pytest.raises(ValueError, match="immutable"):
        store.save_plan(changed_plan)


def test_artifact_registration_is_content_addressed_versioned_and_idempotent(tmp_path):
    store = initialized_store(tmp_path)
    work_file = store.project_dir / "work_items" / "literature" / "report.md"
    work_file.parent.mkdir(parents=True)
    work_file.write_text("version one\n", encoding="utf-8")

    first = store.register_artifact(work_file, "literature", "report", "text/markdown")
    duplicate = store.register_artifact(work_file, "literature", "report", "text/markdown")
    work_file.write_text("version two\n", encoding="utf-8")
    second = store.register_artifact(work_file, "literature", "report", "text/markdown")

    assert duplicate == first
    assert first.version == 1
    assert second.version == 2
    assert first.sha256 != second.sha256
    assert store.artifact_path(first).read_text(encoding="utf-8") == "version one\n"
    assert store.artifact_path(second).read_text(encoding="utf-8") == "version two\n"
    assert len(store.read_artifacts()) == 2
    store.assert_integrity()


def test_artifact_source_and_uri_cannot_escape_project(tmp_path):
    store = initialized_store(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("not project evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="inside the project"):
        store.register_artifact(outside, "literature", "outside", "text/plain")

    artifact_file = store.project_dir / "inside.txt"
    artifact_file.write_text("inside", encoding="utf-8")
    artifact = store.register_artifact(artifact_file, "literature", "inside", "text/plain")
    escaped = artifact.model_copy(update={"uri": "project://../outside.txt"})
    with pytest.raises(ValueError, match="escapes"):
        store.artifact_path(escaped)

    with pytest.raises(ValueError, match="unsafe project_id"):
        ResearchProjectStore(tmp_path / "projects", "../escaped")


def test_integrity_detects_artifact_tampering_and_missing_references(tmp_path):
    store = initialized_store(tmp_path)
    work_file = store.project_dir / "source.txt"
    work_file.write_text("original", encoding="utf-8")
    artifact = store.register_artifact(work_file, "literature", "source", "text/plain")
    store.artifact_path(artifact).write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact (size|digest) mismatch"):
        store.assert_integrity()

    other = initialized_store(tmp_path / "other")
    other.save_work_item_result(WorkItemResult(
        item_id="literature",
        module="literature_search",
        status=WorkItemStatus.COMPLETED,
        summary="Bad artifact reference.",
        artifact_ids=["artifact-missing"],
    ))
    with pytest.raises(ValueError, match="missing artifacts"):
        other.assert_integrity()


def test_integrity_rejects_non_monotonic_event_ledger(tmp_path):
    store = initialized_store(tmp_path)
    store.append_event("created", "draft")
    event_path = store.project_dir / "events.jsonl"
    payload = json.loads(event_path.read_text(encoding="utf-8").strip())
    payload["sequence"] = 3
    event_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sequence"):
        store.assert_integrity()


def test_execution_lock_prevents_concurrent_state_machines(tmp_path):
    store = initialized_store(tmp_path)
    second_instance = ResearchProjectStore(tmp_path / "projects", "project-test")
    with store.execution_lock():
        with pytest.raises(ProjectBusyError, match="already executing"):
            with second_instance.execution_lock():
                raise AssertionError("second execution lock must not be acquired")


def test_domain_activity_ledger_is_sequenced_idempotent_and_source_linked(tmp_path):
    store = initialized_store(tmp_path)
    trace = TraceEvent(
        run_id="target-project-test",
        task_id="task-test",
        event_type="tool_result",
        state="tool_execution",
        detail={
            "tool": "europe_pmc_rag",
            "status": "partial",
            "coverage_status": "partial",
            "context_match_score": 0.8,
        },
        related_ids=["tool-test"],
    )
    trace_path = store.project_dir / "work_items" / "literature" / "trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(trace.model_dump_json() + "\n", encoding="utf-8")
    store.register_artifact(
        trace_path, "literature", "target_discovery_trace", "application/x-ndjson",
    )
    projection = project_trace_event(
        project_id=store.project_id,
        work_item_id="literature",
        child_run_id=trace.run_id,
        event=trace,
        descriptors=[ToolDescriptor(
            tool_id="europe_pmc_rag",
            evidence_dimension="literature",
            description="Literature retrieval and grounded extraction.",
        )],
    )

    first = store.append_domain_activity(projection)
    duplicate = store.append_domain_activity(projection)

    assert first == duplicate
    assert first.sequence == 1
    assert store.domain_activity_cursor() == 1
    assert store.read_domain_activities(after_sequence=1) == []
    assert store.read_domain_activities(limit=1) == [first]
    store.assert_integrity()

    ledger = store.project_dir / "domain_activities.jsonl"
    tampered = json.loads(ledger.read_text(encoding="utf-8"))
    tampered["source_event_sha256"] = "0" * 64
    ledger.write_text(json.dumps(tampered) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source digest mismatch"):
        store.assert_integrity()


def test_domain_activity_integrity_rejects_sequence_and_source_tampering(tmp_path):
    store = initialized_store(tmp_path)
    path = store.project_dir / "domain_activities.jsonl"
    path.write_text(json.dumps({
        "contract_version": "3.0.0",
        "sequence": 2,
        "activity_id": "trace-one",
        "project_id": store.project_id,
        "work_item_id": "literature",
        "child_run_id": "target-project-test",
        "source_contract_version": "2.2.0",
        "source_trace_id": "trace-one",
        "source_event_sha256": "0" * 64,
        "stage": "literature",
        "activity_type": "tool_call",
        "status": "running",
        "source_state": "tool_execution",
        "related_ids": [],
        "summary": "Started a literature tool.",
        "detail": {},
        "created_at": "2026-08-05T00:00:00Z",
    }) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="sequence"):
        store.assert_integrity()
