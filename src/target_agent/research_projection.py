"""Safe product projections of the authoritative disease-target trace ledger."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable

from .contracts import ToolDescriptor, TraceEvent
from .research_contracts import (
    DomainActivityRecord,
    DomainActivityStatus,
    DomainStage,
)


_DIMENSION_STAGE = {
    "scope": DomainStage.DATASET_DISCOVERY,
    "dataset_discovery": DomainStage.DATASET_DISCOVERY,
    "genetics": DomainStage.GENETICS,
    "omics": DomainStage.OMICS,
    "pathway": DomainStage.OMICS,
    "literature": DomainStage.LITERATURE,
    "perturbation": DomainStage.PERTURBATION,
    "causal_gold": DomainStage.PERTURBATION,
    "drug": DomainStage.DRUG_SAFETY,
    "multi_evidence": DomainStage.EVIDENCE_INTEGRATION,
}

_SAFE_DETAIL_KEYS = {
    "state_transition": ("resume",),
    "plan": ("planner_backend", "fallback_used", "steps"),
    "tool_call": ("tool", "step_id", "repair_round", "reason"),
    "tool_result": (
        "tool", "status", "coverage_status", "context_match_score",
        "repair_round",
    ),
    "review": ("round", "blocking", "major", "minor", "reviewer_backend"),
    "replan": ("round", "action", "tools", "outcomes"),
    "checkpoint": ("stage", "completed_steps", "tool_calls"),
    "ranking": (),
    "report": ("status",),
    "degradation": ("reason",),
    "refusal": ("reason",),
}


def _safe_detail(event: TraceEvent) -> dict[str, Any]:
    return {
        key: event.detail[key]
        for key in _SAFE_DETAIL_KEYS[event.event_type]
        if key in event.detail
    }


def _stage(event: TraceEvent, evidence_dimension: str | None) -> DomainStage:
    if event.state in {"reviewer", "reviewer_repair"}:
        return DomainStage.RELIABILITY_REVIEW
    if event.event_type == "state_transition":
        return DomainStage.INTAKE
    if event.event_type == "plan":
        return DomainStage.PLANNING
    if event.event_type == "review":
        return DomainStage.RELIABILITY_REVIEW
    if event.event_type == "replan":
        return DomainStage.DATASET_DISCOVERY
    if event.event_type == "checkpoint":
        return DomainStage.RELIABILITY_BOUNDARY
    if event.event_type == "ranking":
        return DomainStage.RANKING_EXPERIMENTS
    if event.event_type == "report":
        return DomainStage.REPORTING
    if event.event_type in {"degradation", "refusal"}:
        return DomainStage.RELIABILITY_BOUNDARY
    return _DIMENSION_STAGE.get(evidence_dimension or "", DomainStage.EVIDENCE_INTEGRATION)


def _status(event: TraceEvent) -> DomainActivityStatus:
    if event.event_type == "plan":
        return DomainActivityStatus.PLANNED
    if event.event_type == "tool_call":
        return DomainActivityStatus.RUNNING
    if event.event_type == "tool_result":
        value = event.detail.get("status")
        try:
            return DomainActivityStatus(str(value))
        except ValueError:
            return DomainActivityStatus.RECORDED
    if event.event_type == "review":
        return DomainActivityStatus.REVIEWED
    if event.event_type == "replan":
        return DomainActivityStatus.REPLANNED
    if event.event_type == "checkpoint":
        return DomainActivityStatus.CHECKPOINTED
    if event.event_type == "ranking":
        return DomainActivityStatus.COMPLETED
    if event.event_type == "report":
        value = event.detail.get("status")
        try:
            return DomainActivityStatus(str(value))
        except ValueError:
            return DomainActivityStatus.COMPLETED
    if event.event_type == "degradation":
        return DomainActivityStatus.DEGRADED
    if event.event_type == "refusal":
        return DomainActivityStatus.REFUSED
    return DomainActivityStatus.RECORDED


def _summary(event: TraceEvent, tool_name: str | None) -> str:
    if event.event_type == "tool_call":
        return f"Started allowlisted tool {tool_name}."
    if event.event_type == "tool_result":
        return (
            f"Tool {tool_name} returned {event.detail.get('status', 'unknown')} with "
            f"{event.detail.get('coverage_status', 'unknown')} coverage."
        )
    if event.event_type == "review":
        return (
            "Reviewer recorded "
            f"{event.detail.get('blocking', 0)} blocking, "
            f"{event.detail.get('major', 0)} major and "
            f"{event.detail.get('minor', 0)} minor findings."
        )
    if event.event_type == "replan":
        if event.state == "reviewer_repair":
            prefix = "Reviewer-driven repair"
        elif event.state == "reviewer":
            prefix = "Reviewer workflow decision"
        else:
            prefix = "Workflow revision"
        return f"{prefix}: {event.detail.get('action', 'recorded revision')}."
    if event.event_type == "ranking":
        return "Completed the governed ranking and falsifiable experiment-design stage."
    if event.event_type == "report":
        return f"Generated the source-bounded report with status {event.detail.get('status', 'unknown')}."
    if event.event_type == "plan":
        return f"Froze an execution plan with {len(event.detail.get('steps') or [])} typed steps."
    if event.event_type == "checkpoint":
        return f"Persisted child workflow checkpoint {event.detail.get('stage', event.state)}."
    if event.event_type in {"degradation", "refusal"}:
        return str(event.detail.get("reason") or f"Workflow recorded {event.event_type}.")
    return f"Child workflow entered {event.state}."


@dataclass(frozen=True)
class DomainActivityProjection:
    """Validated mapping payload before the project store assigns sequence."""

    values: dict[str, Any]

    def to_record(self, sequence: int) -> DomainActivityRecord:
        return DomainActivityRecord(sequence=sequence, **self.values)


def trace_event_digest(event: TraceEvent | dict[str, Any]) -> str:
    payload = event.model_dump(mode="json") if isinstance(event, TraceEvent) else event
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def project_trace_event(
    *,
    project_id: str,
    work_item_id: str,
    child_run_id: str,
    event: TraceEvent,
    descriptors: Iterable[ToolDescriptor],
) -> DomainActivityProjection:
    """Project one child trace event without copying scientific payloads."""
    tool_name = str(event.detail.get("tool")) if event.detail.get("tool") else None
    dimensions = {row.tool_id: row.evidence_dimension for row in descriptors}
    evidence_dimension = dimensions.get(tool_name) if tool_name else None
    coverage = event.detail.get("coverage_status")
    if coverage not in {"covered", "partial", "not_covered", "unknown"}:
        coverage = None
    context_match = event.detail.get("context_match_score")
    if not isinstance(context_match, (int, float)) or isinstance(context_match, bool):
        context_match = None
    return DomainActivityProjection(values={
        "activity_id": event.event_id,
        "project_id": project_id,
        "work_item_id": work_item_id,
        "child_run_id": child_run_id,
        "source_contract_version": event.contract_version,
        "source_trace_id": event.event_id,
        "source_event_sha256": trace_event_digest(event),
        "stage": _stage(event, evidence_dimension),
        "activity_type": event.event_type,
        "status": _status(event),
        "source_state": event.state,
        "evidence_dimension": evidence_dimension,
        "tool_name": tool_name,
        "plan_step_id": (str(event.detail["step_id"]) if event.detail.get("step_id") else None),
        "coverage_status": coverage,
        "context_match_score": float(context_match) if context_match is not None else None,
        "related_ids": event.related_ids,
        "summary": _summary(event, tool_name),
        "detail": _safe_detail(event),
        "created_at": event.created_at,
    })


def summarize_domain_activities(records: Iterable[DomainActivityRecord]) -> list[dict[str, Any]]:
    """Return a compact, deterministic stage index for HTTP/MCP/report clients."""
    summaries: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record.stage.value
        row = summaries.setdefault(key, {
            "stage": key,
            "statuses": [],
            "activity_count": 0,
            "tools": [],
            "latest_tool_status": {},
            "coverage_statuses": [],
            "reviewer_replans": 0,
        })
        if record.status.value not in row["statuses"]:
            row["statuses"].append(record.status.value)
        row["activity_count"] += 1
        if record.tool_name and record.tool_name not in row["tools"]:
            row["tools"].append(record.tool_name)
        if record.tool_name:
            row["latest_tool_status"][record.tool_name] = record.status.value
        if record.coverage_status and record.coverage_status not in row["coverage_statuses"]:
            row["coverage_statuses"].append(record.coverage_status)
        if record.activity_type == "replan" and record.source_state == "reviewer_repair":
            row["reviewer_replans"] += 1
    return list(summaries.values())


__all__ = [
    "DomainActivityProjection", "project_trace_event", "summarize_domain_activities",
    "trace_event_digest",
]
