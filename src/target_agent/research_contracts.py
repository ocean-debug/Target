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


class ProjectEvent(ResearchContract):
    sequence: int = Field(ge=1)
    project_id: str
    event_type: str
    state: str
    work_item_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class ProjectState(ResearchContract):
    project_id: str
    status: ProjectStatus = ProjectStatus.DRAFT
    current_item_id: str | None = None
    completed_items: list[str] = Field(default_factory=list)
    failed_items: list[str] = Field(default_factory=list)
    attempts: dict[str, int] = Field(default_factory=dict)
    terminal_reason: str | None = None
    updated_at: str = Field(default_factory=utc_now)


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
    "DecisionEvent", "ProjectEvent", "ProjectState", "ProjectStatus", "ResearchGoal",
    "ResearchPlan", "ResearchProjectSpec", "TERMINAL_WORK_ITEM_STATUSES", "WorkItemResult",
    "WorkItemSpec", "WorkItemStatus",
]
