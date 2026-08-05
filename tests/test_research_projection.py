from target_agent.contracts import ToolDescriptor, TraceEvent
from target_agent.research_contracts import DomainActivityStatus, DomainStage
from target_agent.research_projection import project_trace_event, summarize_domain_activities


def descriptor() -> ToolDescriptor:
    return ToolDescriptor(
        tool_id="bulk_expression_analysis",
        evidence_dimension="omics",
        description="Deterministic bulk expression wrapper.",
    )


def test_projection_keeps_operational_status_but_not_scientific_payloads():
    event = TraceEvent(
        run_id="target-project-test",
        task_id="task-test",
        event_type="tool_result",
        state="tool_execution",
        detail={
            "tool": "bulk_expression_analysis",
            "status": "success",
            "coverage_status": "covered",
            "context_match_score": 0.9,
            "candidate_genes_emitted": 12,
            "highlighted_targets": ["GENE1"],
            "provider_request": {"request_id": "internal"},
        },
        related_ids=["tool-one", "evidence-one"],
    )

    record = project_trace_event(
        project_id="project-test",
        work_item_id="target_discovery",
        child_run_id=event.run_id,
        event=event,
        descriptors=[descriptor()],
    ).to_record(1)

    assert record.stage == DomainStage.OMICS
    assert record.status == DomainActivityStatus.SUCCESS
    assert record.source_trace_id == event.event_id
    assert record.source_contract_version == event.contract_version
    assert record.detail == {
        "tool": "bulk_expression_analysis",
        "status": "success",
        "coverage_status": "covered",
        "context_match_score": 0.9,
    }
    serialized = record.model_dump_json()
    for prohibited in ("GENE1", "candidate_genes", "provider_request", "highlighted_targets"):
        assert prohibited not in serialized


def test_reviewer_repair_is_a_reliability_stage_and_summary_counts_only_real_repairs():
    tool_event = TraceEvent(
        run_id="target-project-test",
        task_id="task-test",
        event_type="tool_call",
        state="reviewer_repair",
        detail={"tool": "bulk_expression_analysis", "repair_round": 1},
    )
    replan_event = TraceEvent(
        run_id="target-project-test",
        task_id="task-test",
        event_type="replan",
        state="reviewer_repair",
        detail={"round": 1, "action": "retry_failed_read_only_connectors"},
    )
    records = [
        project_trace_event(
            project_id="project-test",
            work_item_id="target_discovery",
            child_run_id=event.run_id,
            event=event,
            descriptors=[descriptor()],
        ).to_record(index)
        for index, event in enumerate((tool_event, replan_event), start=1)
    ]

    assert all(record.stage == DomainStage.RELIABILITY_REVIEW for record in records)
    summary = summarize_domain_activities(records)
    assert summary == [{
        "stage": "reliability_review",
        "statuses": ["running", "replanned"],
        "activity_count": 2,
        "tools": ["bulk_expression_analysis"],
        "latest_tool_status": {"bulk_expression_analysis": "running"},
        "coverage_statuses": [],
        "reviewer_replans": 1,
    }]


def test_tool_execution_revision_is_not_reported_as_reviewer_repair():
    replan = TraceEvent(
        run_id="target-project-test",
        task_id="task-test",
        event_type="replan",
        state="tool_execution",
        detail={"round": 1, "action": "selected_next_eligible_dataset"},
    )
    checkpoint = TraceEvent(
        run_id="target-project-test",
        task_id="task-test",
        event_type="checkpoint",
        state="tool_execution",
        detail={"stage": "tool_execution", "tool_calls": 2},
    )
    rows = [
        project_trace_event(
            project_id="project-test", work_item_id="target_discovery",
            child_run_id=event.run_id, event=event, descriptors=[],
        ).to_record(index)
        for index, event in enumerate((replan, checkpoint), start=1)
    ]

    assert rows[0].stage == DomainStage.DATASET_DISCOVERY
    assert rows[0].summary.startswith("Workflow revision:")
    assert "Reviewer" not in rows[0].summary
    assert rows[1].stage == DomainStage.RELIABILITY_BOUNDARY

    reviewer_replan = TraceEvent(
        run_id="target-project-test", task_id="task-test",
        event_type="replan", state="reviewer",
        detail={"round": 2, "action": "retain_unresolved_evidence_gaps"},
    )
    reviewer_row = project_trace_event(
        project_id="project-test", work_item_id="target_discovery",
        child_run_id=reviewer_replan.run_id, event=reviewer_replan, descriptors=[],
    ).to_record(3)
    assert reviewer_row.stage == DomainStage.RELIABILITY_REVIEW
    assert reviewer_row.summary.startswith("Reviewer workflow decision:")
