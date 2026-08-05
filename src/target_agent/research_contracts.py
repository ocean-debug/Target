"""Versioned contracts for durable, project-level scientific research."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import new_id, utc_now


RESEARCH_CONTRACT_VERSION = "3.0.0"


class ResearchContract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    contract_version: Literal["3.0.0"] = RESEARCH_CONTRACT_VERSION


class AutonomyMode(str, Enum):
    AUTONOMOUS = "autonomous"
    CHECKPOINTED = "checkpointed"
    SUPERVISED = "supervised"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    COMPLETED_WITH_GAPS = "completed_with_gaps"
    NEEDS_INPUT = "needs_input"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkItemStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_GAPS = "completed_with_gaps"
    NEEDS_INPUT = "needs_input"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class FailureClass(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    MISSING_INPUT = "missing_input"
    SCIENTIFIC_GAP = "scientific_gap"
    INTEGRITY_FAILURE = "integrity_failure"
    UNSUPPORTED = "unsupported"
    INTERNAL = "internal"


class RepairAction(str, Enum):
    RERUN_SUBGRAPH_SAME_INPUTS = "rerun_subgraph_same_inputs"
    REQUEST_INPUT = "request_input"
    RETAIN_GAP = "retain_gap"
    STOP = "stop"


class RepairRisk(str, Enum):
    R0_DERIVATION_ONLY = "R0_derivation_only"
    R1_SAME_SCOPE_READ_ONLY = "R1_same_scope_read_only"
    R2_SCIENTIFIC_METHOD_CHANGE = "R2_scientific_method_change"
    R3_SCOPE_OR_TRUTH_CHANGE = "R3_scope_or_truth_change"


class RepairAuthorization(str, Enum):
    AUTOMATIC = "automatic"
    CHECKPOINT_REQUIRED = "checkpoint_required"
    HUMAN_INPUT_REQUIRED = "human_input_required"
    PROHIBITED = "prohibited"


class RepairResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    MITIGATED = "mitigated"
    UNRESOLVED = "unresolved"
    EXHAUSTED = "exhausted"


class DomainStage(str, Enum):
    """Stable product-facing stages projected from the vertical child run."""

    INTAKE = "intake"
    PLANNING = "planning"
    DATASET_DISCOVERY = "dataset_discovery"
    GENETICS = "genetics"
    OMICS = "omics"
    LITERATURE = "literature"
    PERTURBATION = "perturbation"
    DRUG_SAFETY = "drug_safety"
    EVIDENCE_INTEGRATION = "evidence_integration"
    RELIABILITY_REVIEW = "reliability_review"
    RANKING_EXPERIMENTS = "ranking_and_experiment_design"
    REPORTING = "reporting"
    RELIABILITY_BOUNDARY = "reliability_boundary"


class DomainActivityStatus(str, Enum):
    RECORDED = "recorded"
    PLANNED = "planned"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    OUT_OF_SCOPE = "out_of_scope"
    REVIEWED = "reviewed"
    REPLANNED = "replanned"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"
    COMPLETED_WITH_GAPS = "completed_with_gaps"
    NEEDS_INPUT = "needs_input"
    DEGRADED = "degraded"
    REFUSED = "refused"


class AssessmentLevel(str, Enum):
    A0 = "A0"  # deterministic integrity checks
    A1 = "A1"  # model-assisted review
    A2 = "A2"  # independent model or rerun
    A3 = "A3"  # domain specialist review
    HUMAN = "human"


class AssessmentDimension(str, Enum):
    INTEGRITY = "integrity"
    PROVENANCE = "provenance"
    ENTAILMENT = "entailment"
    METHODOLOGY = "methodology"
    APPLICABILITY = "applicability"
    REPRODUCIBILITY = "reproducibility"
    SCHEMA_ALIGNMENT = "schema_alignment"


class AssessmentResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"
    NOT_ASSESSED = "not_assessed"


class DecisionAction(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    REPLAN = "replan"
    REQUEST_EVIDENCE = "request_evidence"
    OVERRIDE = "override"
    RELEASE = "release"


class DataContract(ResearchContract):
    """Small deterministic boundary contract; no runtime JSON-schema dependency."""

    schema_id: str = Field(min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)
    required_fields: list[str] = Field(default_factory=list)
    field_types: dict[str, Literal["string", "number", "integer", "boolean", "object", "array"]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def required_fields_have_types(self) -> "DataContract":
        missing = set(self.required_fields) - set(self.field_types)
        if missing:
            raise ValueError(f"required fields have no declared type: {sorted(missing)}")
        return self


class ResearchGoal(ResearchContract):
    question: str = Field(min_length=3)
    success_criteria: list[str] = Field(min_length=1)
    deliverables: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)


class ResearchProjectSpec(ResearchContract):
    project_id: str = Field(default_factory=lambda: new_id("project"), pattern=r"^project-[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=3)
    domain: Literal["disease_target_discovery", "life_science"] = "disease_target_discovery"
    goal: ResearchGoal
    context: dict[str, Any] = Field(default_factory=dict)
    autonomy_mode: AutonomyMode = AutonomyMode.CHECKPOINTED
    max_work_items: int = Field(default=12, ge=1, le=30)
    max_replans: int = Field(default=2, ge=0, le=2)
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def reject_embedded_credentials(self) -> "ResearchProjectSpec":
        blocked = {
            "api_key", "apikey", "access_key", "authorization", "credential", "credentials",
            "password", "private_key", "secret", "token",
        }

        def visit(value: Any, path: str) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    normalized = str(key).strip().lower().replace("-", "_")
                    if normalized in blocked or normalized.endswith("_api_key") or normalized.endswith("_token"):
                        raise ValueError(f"project context cannot contain credentials: {path}.{key}")
                    visit(item, f"{path}.{key}")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    visit(item, f"{path}[{index}]")

        visit(self.context, "context")
        return self


class WorkItemSpec(ResearchContract):
    item_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=2)
    module: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    objective: str = Field(min_length=3)
    dependencies: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    input_contract: DataContract | None = None
    output_contract: DataContract | None = None
    acceptance_criteria: list[str] = Field(min_length=1)
    required: bool = True
    review_level: AssessmentLevel = AssessmentLevel.A0
    max_attempts: int = Field(default=1, ge=1, le=3)
    rerun_of_item_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    repair_request_id: str | None = Field(default=None, pattern=r"^repair-[a-f0-9]{24}$")

    @model_validator(mode="after")
    def bind_repair_metadata(self) -> "WorkItemSpec":
        if (self.rerun_of_item_id is None) != (self.repair_request_id is None):
            raise ValueError("rerun_of_item_id and repair_request_id must be set together")
        return self


class ResearchPlan(ResearchContract):
    plan_id: str = Field(default_factory=lambda: new_id("plan"))
    project_id: str
    items: list[WorkItemSpec] = Field(min_length=1)
    planner_backend: str
    rationale: str
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_dag(self) -> "ResearchPlan":
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("work item ids must be unique")
        known = set(ids)
        for item in self.items:
            unknown = set(item.dependencies) - known
            if unknown:
                raise ValueError(f"work item {item.item_id} has unknown dependencies: {sorted(unknown)}")
            if item.item_id in item.dependencies:
                raise ValueError(f"work item {item.item_id} cannot depend on itself")
        visiting: set[str] = set()
        visited: set[str] = set()
        edges = {item.item_id: item.dependencies for item in self.items}

        def visit(item_id: str) -> None:
            if item_id in visiting:
                raise ValueError("research plan contains a dependency cycle")
            if item_id in visited:
                return
            visiting.add(item_id)
            for dependency in edges[item_id]:
                visit(dependency)
            visiting.remove(item_id)
            visited.add(item_id)

        for item_id in ids:
            visit(item_id)
        return self


class ArtifactRecord(ResearchContract):
    artifact_id: str = Field(default_factory=lambda: new_id("artifact"))
    project_id: str
    work_item_id: str
    logical_name: str = Field(min_length=1)
    uri: str = Field(pattern=r"^project://")
    media_type: str = "application/octet-stream"
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    version: int = Field(default=1, ge=1)
    created_at: str = Field(default_factory=utc_now)


class WorkItemResult(ResearchContract):
    item_id: str
    module: str
    status: WorkItemStatus
    summary: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error: str | None = None
    failure_class: FailureClass | None = None
    input_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    supersedes_result_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    repair_request_id: str | None = Field(default=None, pattern=r"^repair-[a-f0-9]{24}$")
    started_at: str = Field(default_factory=utc_now)
    completed_at: str = Field(default_factory=utc_now)


class AssessmentRecord(ResearchContract):
    assessment_id: str = Field(default_factory=lambda: new_id("assessment"))
    project_id: str
    target_id: str
    target_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    dimension: AssessmentDimension
    level: AssessmentLevel
    result: AssessmentResult
    actor: str
    method: str
    rationale: str
    blocking: bool = False
    created_at: str = Field(default_factory=utc_now)


class DecisionEvent(ResearchContract):
    decision_id: str = Field(default_factory=lambda: new_id("decision"))
    project_id: str
    action: DecisionAction
    target_ids: list[str]
    rationale: str
    actor: str
    evidence_snapshot_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reversible: bool = True
    created_at: str = Field(default_factory=utc_now)


class RepairRequest(ResearchContract):
    """Immutable assessment-triggered request evaluated by deterministic policy."""

    repair_request_id: str = Field(pattern=r"^repair-[a-f0-9]{24}$")
    project_id: str
    base_plan_id: str
    target_work_item_id: str
    trigger_assessment_ids: list[str] = Field(min_length=1)
    trigger_result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    trigger_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    failure_class: FailureClass
    action: RepairAction
    risk: RepairRisk
    authorization: RepairAuthorization
    affected_work_item_ids: list[str] = Field(min_length=1)
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_rule_id: str
    policy_version: str = "1.0.0"
    success_criteria: list[str] = Field(min_length=1)
    rationale: str
    created_at: str = Field(default_factory=utc_now)


class ResearchPlanRevision(ResearchContract):
    """Append-only execution overlay; never a free-form replacement plan."""

    revision_id: str = Field(pattern=r"^revision-[a-f0-9]{24}$")
    project_id: str
    base_plan_id: str
    parent_revision_id: str | None = Field(default=None, pattern=r"^revision-[a-f0-9]{24}$")
    revision_number: int = Field(ge=1, le=2)
    repair_request_id: str = Field(pattern=r"^repair-[a-f0-9]{24}$")
    operation: Literal["rerun_subgraph_same_inputs"] = "rerun_subgraph_same_inputs"
    added_items: list[WorkItemSpec] = Field(min_length=1)
    superseded_item_ids: list[str] = Field(min_length=1)
    superseded_assessment_ids: list[str] = Field(default_factory=list)
    trigger_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_required: bool
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_overlay(self) -> "ResearchPlanRevision":
        added_ids = [item.item_id for item in self.added_items]
        if len(added_ids) != len(set(added_ids)):
            raise ValueError("plan revision added item ids must be unique")
        if set(added_ids) & set(self.superseded_item_ids):
            raise ValueError("plan revision cannot add and supersede the same item id")
        if any(item.repair_request_id != self.repair_request_id for item in self.added_items):
            raise ValueError("every revision item must bind to the revision repair request")
        return self


class RepairResolution(ResearchContract):
    resolution_id: str = Field(pattern=r"^resolution-[a-f0-9]{24}$")
    project_id: str
    repair_request_id: str = Field(pattern=r"^repair-[a-f0-9]{24}$")
    revision_id: str = Field(pattern=r"^revision-[a-f0-9]{24}$")
    status: RepairResolutionStatus
    before_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_assessment_ids: list[str] = Field(default_factory=list)
    active_work_item_ids: list[str] = Field(default_factory=list)
    rationale: str
    created_at: str = Field(default_factory=utc_now)


class RepairQueueSnapshot(ResearchContract):
    project_id: str
    requests: list[RepairRequest] = Field(default_factory=list)
    revisions: list[ResearchPlanRevision] = Field(default_factory=list)
    resolutions: list[RepairResolution] = Field(default_factory=list)
    remaining_replans: int = Field(ge=0, le=2)


class ProjectEvent(ResearchContract):
    sequence: int = Field(ge=1)
    project_id: str
    event_type: str
    state: str
    work_item_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class DomainActivityRecord(ResearchContract):
    """Read-only projection of one authoritative child-workflow TraceEvent.

    This record is an observability index. Scientific facts, numeric results and
    provenance remain authoritative in the child EvidenceStore referenced by
    ``child_run_id`` and ``source_trace_id``.
    """

    sequence: int = Field(ge=1)
    activity_id: str = Field(pattern=r"^trace-[A-Za-z0-9][A-Za-z0-9._-]*$")
    project_id: str
    work_item_id: str
    child_run_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    source_contract_version: str
    source_trace_id: str = Field(pattern=r"^trace-[A-Za-z0-9][A-Za-z0-9._-]*$")
    source_event_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stage: DomainStage
    activity_type: Literal[
        "state_transition", "plan", "tool_call", "tool_result", "review",
        "replan", "checkpoint", "ranking", "report", "degradation", "refusal",
    ]
    status: DomainActivityStatus
    source_state: str
    evidence_dimension: str | None = None
    tool_name: str | None = None
    plan_step_id: str | None = None
    coverage_status: Literal["covered", "partial", "not_covered", "unknown"] | None = None
    context_match_score: float | None = Field(default=None, ge=0.0, le=1.0)
    related_ids: list[str] = Field(default_factory=list)
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def preserve_source_identity(self) -> "DomainActivityRecord":
        if self.activity_id != self.source_trace_id:
            raise ValueError("domain activity id must equal its authoritative source trace id")
        return self


class ProjectState(ResearchContract):
    project_id: str
    status: ProjectStatus = ProjectStatus.DRAFT
    current_item_id: str | None = None
    completed_items: list[str] = Field(default_factory=list)
    failed_items: list[str] = Field(default_factory=list)
    attempts: dict[str, int] = Field(default_factory=dict)
    checkpoint_kind: Literal["plan", "work_item", "repair", "release"] | None = None
    checkpoint_target_id: str | None = None
    checkpoint_snapshot_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    terminal_reason: str | None = None
    updated_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def bind_checkpoint_state(self) -> "ProjectState":
        if self.checkpoint_kind is None:
            if self.checkpoint_target_id is not None or self.checkpoint_snapshot_digest is not None:
                raise ValueError("checkpoint metadata requires checkpoint_kind")
            return self
        if not self.checkpoint_target_id:
            raise ValueError("checkpoint_kind requires checkpoint_target_id")
        if self.checkpoint_kind in {"repair", "release"} and self.checkpoint_snapshot_digest is None:
            raise ValueError("repair/release checkpoint requires snapshot digest")
        return self


class DomainActivityPage(ResearchContract):
    project_id: str
    activities: list[DomainActivityRecord]
    next_cursor: int = Field(ge=0)
    has_more: bool

    @model_validator(mode="after")
    def preserve_project_identity(self) -> "DomainActivityPage":
        if any(row.project_id != self.project_id for row in self.activities):
            raise ValueError("domain activity page contains another project's record")
        return self


class ResearchProjectSnapshot(ResearchContract):
    spec: ResearchProjectSpec
    state: ProjectState | None = None
    plan: ResearchPlan | None = None
    work_item_results: list[WorkItemResult] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    assessments: list[AssessmentRecord] = Field(default_factory=list)
    decisions: list[DecisionEvent] = Field(default_factory=list)
    event_cursor: int = Field(default=0, ge=0)
    domain_activity_cursor: int = Field(default=0, ge=0)
    domain_stage_summary: list[dict[str, Any]] = Field(default_factory=list)
    repair_requests: list[RepairRequest] = Field(default_factory=list)
    plan_revisions: list[ResearchPlanRevision] = Field(default_factory=list)
    repair_resolutions: list[RepairResolution] = Field(default_factory=list)
    active_work_item_ids: list[str] = Field(default_factory=list)
    release_snapshot_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    next_actions: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def preserve_project_identity(self) -> "ResearchProjectSnapshot":
        project_id = self.spec.project_id
        project_records: list[Any] = [
            *self.artifacts, *self.assessments, *self.decisions, *self.repair_requests,
            *self.plan_revisions, *self.repair_resolutions,
        ]
        if self.state is not None:
            project_records.append(self.state)
        if self.plan is not None:
            project_records.append(self.plan)
        if any(getattr(row, "project_id", project_id) != project_id for row in project_records):
            raise ValueError("project snapshot contains another project's record")
        return self


TERMINAL_WORK_ITEM_STATUSES = frozenset({
    WorkItemStatus.COMPLETED,
    WorkItemStatus.COMPLETED_WITH_GAPS,
    WorkItemStatus.NEEDS_INPUT,
    WorkItemStatus.BLOCKED,
    WorkItemStatus.FAILED,
    WorkItemStatus.SKIPPED,
})


__all__ = [
    "RESEARCH_CONTRACT_VERSION", "ArtifactRecord", "AssessmentDimension", "AssessmentLevel",
    "AssessmentRecord", "AssessmentResult", "AutonomyMode", "DataContract", "DecisionAction",
    "DecisionEvent", "DomainActivityPage", "DomainActivityRecord", "DomainActivityStatus", "DomainStage",
    "FailureClass", "ProjectEvent", "ProjectState", "ProjectStatus", "RepairAction",
    "RepairAuthorization", "RepairQueueSnapshot", "RepairRequest", "RepairResolution",
    "RepairResolutionStatus", "RepairRisk", "ResearchGoal", "ResearchPlan", "ResearchPlanRevision",
    "ResearchProjectSnapshot", "ResearchProjectSpec", "TERMINAL_WORK_ITEM_STATUSES",
    "WorkItemResult", "WorkItemSpec", "WorkItemStatus",
]
