"""Versioned public contracts for every TargetDiscovery Agent boundary."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "2.0.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    contract_version: Literal["2.0.0"] = CONTRACT_VERSION


class ClaimClass(str, Enum):
    FACT = "FACT"
    OBSERVED = "OBSERVED"
    PREDICTED = "PREDICTED"
    INFERRED = "INFERRED"


class Stance(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class ToolStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    OUT_OF_SCOPE = "out_of_scope"


class CoverageStatus(str, Enum):
    COVERED = "covered"
    PARTIAL = "partial"
    NOT_COVERED = "not_covered"
    UNKNOWN = "unknown"


class TerminalStatus(str, Enum):
    COMPLETED = "completed"
    COMPLETED_WITH_GAPS = "completed_with_gaps"
    NEEDS_INPUT = "needs_input"
    REFUSED = "refused"
    FAILED = "failed"


class TaskContext(ContractModel):
    disease: str | None = None
    disease_id: str | None = None
    disease_subtype: str | None = None
    organism: str = "Homo sapiens"
    population: str | None = None
    tissue: str | None = None
    cell_type: str | None = None
    disease_stage: str | None = None
    desired_phenotype: str | None = None
    assay: str | None = None
    perturbation_type: str | None = None


class TaskConstraints(ContractModel):
    public_data_only: bool = True
    druggable_only: bool = False
    max_initial_candidates: int = Field(default=20, ge=1, le=20)
    max_ranked_targets: int = Field(default=10, ge=1, le=50)
    max_target_cards: int = Field(default=5, ge=1, le=10)
    max_review_rounds: int = Field(default=2, ge=0, le=2)
    max_tool_calls: int = Field(default=30, ge=1, le=30)


class TaskSpec(ContractModel):
    task_id: str = Field(default_factory=lambda: new_id("task"))
    task_type: Literal["disease_to_target", "trait_mechanism"]
    question: str = Field(min_length=3)
    context: TaskContext
    constraints: TaskConstraints = Field(default_factory=TaskConstraints)
    candidate_genes: list[str] = Field(default_factory=list)
    requested_outputs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def require_scope(self) -> "TaskSpec":
        if self.task_type == "disease_to_target" and not self.context.disease:
            raise ValueError("disease_to_target requires context.disease")
        if self.task_type == "trait_mechanism" and not self.context.desired_phenotype:
            raise ValueError("trait_mechanism requires context.desired_phenotype")
        return self


class PlanStep(ContractModel):
    step_id: str
    name: str
    tool: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    input_refs: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    degradation_conditions: list[str] = Field(default_factory=list)


class ExecutionPlan(ContractModel):
    plan_id: str = Field(default_factory=lambda: new_id("plan"))
    task_id: str
    planner_backend: str
    steps: list[PlanStep]
    fallback_used: bool = False
    created_at: str = Field(default_factory=utc_now)


class SourceLocator(ContractModel):
    uri: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    version: str | None = None
    section: str | None = None
    chunk_id: str | None = None
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)


class EvidenceContext(ContractModel):
    organism: str | None = None
    population: str | None = None
    tissue: str | None = None
    cell_type: str | None = None
    disease: str | None = None
    disease_stage: str | None = None
    assay: str | None = None
    perturbation_type: str | None = None


class EvidenceItem(ContractModel):
    evidence_id: str = Field(default_factory=lambda: new_id("ev"))
    tool_run_id: str = Field(min_length=1)
    gene_symbol: str | None = None
    claim_class: ClaimClass
    statement: str = Field(min_length=1)
    source: SourceLocator
    source_span: str = Field(min_length=1)
    context: EvidenceContext
    stance: Stance = Stance.UNCERTAIN
    effect_direction: Literal["increase", "decrease", "mixed", "unclear"] = "unclear"
    effect: dict[str, Any] = Field(default_factory=dict)
    uncertainty: str = Field(min_length=1)
    quality_flags: list[str] = Field(default_factory=list)
    context_match_score: float = Field(ge=0.0, le=1.0)


class ToolCapability(ContractModel):
    supported_organisms: list[str] = Field(default_factory=list)
    supported_tissues: list[str] = Field(default_factory=list)
    supported_cell_types: list[str] = Field(default_factory=list)
    supported_perturbations: list[str] = Field(default_factory=list)
    training_scope: str | None = None
    validation_scope: str | None = None


class ArtifactRef(ContractModel):
    name: str
    uri: str
    sha256: str | None = None
    media_type: str | None = None


class ToolResult(ContractModel):
    tool_run_id: str = Field(default_factory=lambda: new_id("tool"))
    tool_name: str
    tool_version: str
    status: ToolStatus
    coverage_status: CoverageStatus
    context_match_score: float = Field(ge=0.0, le=1.0)
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    capability: ToolCapability
    data_version: str | None = None
    code_version: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error: str | None = None
    cached: bool = False
    started_at: str = Field(default_factory=utc_now)
    elapsed_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_status(self) -> "ToolResult":
        if self.coverage_status == CoverageStatus.NOT_COVERED and self.status == ToolStatus.SUCCESS:
            raise ValueError("not_covered cannot be reported as success")
        if self.status == ToolStatus.FAILED and not self.error:
            raise ValueError("failed tool result requires error")
        return self


class Claim(ContractModel):
    claim_id: str = Field(default_factory=lambda: new_id("claim"))
    claim_class: ClaimClass
    statement: str
    evidence_ids: list[str] = Field(min_length=1)
    synthesis_rationale: str | None = None


class ReviewerFinding(ContractModel):
    finding_id: str = Field(default_factory=lambda: new_id("finding"))
    severity: Literal["blocking", "major", "minor"]
    category: Literal[
        "missing_provenance", "context_mismatch", "causal_overreach",
        "conflicting_evidence", "numeric_error", "coverage_gap", "tool_failure",
    ]
    message: str
    related_ids: list[str] = Field(default_factory=list)
    required_action: str
    resolved: bool = False


class GraphNode(ContractModel):
    node_id: str
    node_type: Literal["gene", "program", "trait", "disease", "cell_state", "drug"]
    label: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(ContractModel):
    source: str
    target: str
    relation: str
    evidence_ids: list[str] = Field(default_factory=list)
    claim_class: ClaimClass
    weight: float | None = None


class CausalGraph(ContractModel):
    graph_id: str = Field(default_factory=lambda: new_id("graph"))
    graph_kind: Literal["causal_model", "mechanistic_evidence"]
    context: EvidenceContext
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    model_statistics: dict[str, Any] = Field(default_factory=dict)
    source_artifacts: list[ArtifactRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ExperimentOutcome(ContractModel):
    outcome: Literal["positive", "negative", "contradictory"]
    observation: str
    conclusion: str
    next_action: str


class ExperimentPlan(ContractModel):
    hypothesis: str
    model_system: str
    intervention: str
    direction: Literal["activate", "inhibit", "knockout", "overexpress", "compare"]
    controls: list[str]
    primary_endpoints: list[str]
    secondary_endpoints: list[str]
    replication_and_power: str
    outcomes: list[ExperimentOutcome]
    highest_information_next_experiment: str
    stop_conditions: list[str]


class ScoreBreakdown(ContractModel):
    human_genetics: float = Field(ge=0, le=25)
    disease_omics: float = Field(ge=0, le=20)
    perturbation: float = Field(ge=0, le=20)
    mechanism: float = Field(ge=0, le=15)
    druggability: float = Field(ge=0, le=10)
    safety_translation: float = Field(ge=0, le=10)
    total: float = Field(ge=0, le=100)


class TargetCard(ContractModel):
    target_card_id: str = Field(default_factory=lambda: new_id("card"))
    gene_symbol: str
    rank: int = Field(ge=1)
    decision: Literal["GO", "CONDITIONAL_GO", "NO_GO", "INSUFFICIENT_EVIDENCE"]
    scores: ScoreBreakdown
    evidence_ids: list[str]
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    opposing_evidence_ids: list[str] = Field(default_factory=list)
    safety_blockers: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    matched_drugs: list[dict[str, Any]] = Field(default_factory=list)
    experiment_plan: ExperimentPlan
    limitations: list[str] = Field(default_factory=list)


class TraceEvent(ContractModel):
    event_id: str = Field(default_factory=lambda: new_id("trace"))
    run_id: str
    task_id: str
    event_type: Literal[
        "state_transition", "plan", "tool_call", "tool_result", "review",
        "replan", "checkpoint", "ranking", "report", "degradation", "refusal",
    ]
    state: str
    detail: dict[str, Any] = Field(default_factory=dict)
    related_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class CaseRecord(ContractModel):
    case_id: str = Field(default_factory=lambda: new_id("case"))
    run_id: str
    task_spec: TaskSpec
    plan: ExecutionPlan
    tool_run_ids: list[str]
    finding_ids: list[str]
    revision_history: list[dict[str, Any]]
    final_status: TerminalStatus
    final_claim_ids: list[str]
    scientific_review: Literal["pending", "approved", "rejected"] = "pending"
    promotion_eligible: bool = False
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def prevent_unsafe_promotion(self) -> "CaseRecord":
        if self.promotion_eligible and self.scientific_review != "approved":
            raise ValueError("only scientifically approved cases are promotion eligible")
        return self

