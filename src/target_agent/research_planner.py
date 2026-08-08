"""Constrained planner for durable, project-level research workflows."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from .llm import LLMUnavailable, StepClient
from .research_contracts import (
    DataContract,
    ResearchPlan,
    ResearchProjectSpec,
    WorkItemSpec,
)
from .paper_strategy import PatternStore, PlannerFewShotBuilder, infer_data_availability
from .skill_catalog import SkillCatalog, SkillHintBuilder
from .research_modules import ResearchModuleRegistry


_BASELINE_MODULES = (
    "project_brief",
    "literature_search",
    "hypothesis_generation",
    "independent_review",
    "research_report",
)
_TARGET_MODULE = "target_discovery"
_PROHIBITED_MARKERS = (
    "arbitrary_code",
    "code_execution",
    "command_execution",
    "dynamic_code",
    "python_exec",
    "shell",
)


class PlannerConfigurationError(ValueError):
    """Raised when the registered modules cannot support the safe baseline."""


class _PlannerPayload(BaseModel):
    """The only shape the model may control.

    Identity, contract version and planner provenance are injected locally so a
    model cannot silently move work to another project or rewrite audit fields.
    """

    model_config = ConfigDict(extra="forbid")
    items: list[WorkItemSpec]
    rationale: str


def _output_contract(schema_id: str, **fields: str) -> DataContract:
    return DataContract(
        schema_id=schema_id,
        required_fields=list(fields),
        field_types=fields,
    )


class ResearchPlanner:
    """Create plans exclusively from the live typed module registry."""

    def __init__(
        self,
        registry: ResearchModuleRegistry,
        client: StepClient | None = None,
        pattern_store: PatternStore | None = None,
        few_shot_top_k: int = 3,
        skill_catalog: SkillCatalog | None = None,
        skill_hint_top_k: int = 3,
    ):
        self.registry = registry
        self.client = client
        self.pattern_store = pattern_store
        self.few_shot = PlannerFewShotBuilder(pattern_store, few_shot_top_k)
        self.skill_hints = SkillHintBuilder(skill_catalog, skill_hint_top_k)

    @property
    def capabilities(self) -> list[dict[str, Any]]:
        """Return safe, currently registered capabilities exposed to the model."""
        capabilities: list[dict[str, Any]] = []
        for descriptor in self.registry.public_capabilities():
            if not self._is_safe_descriptor(descriptor):
                continue
            capabilities.append(descriptor)
        return capabilities

    @property
    def allowed_modules(self) -> set[str]:
        return {str(item["name"]) for item in self.capabilities}

    @staticmethod
    def _is_safe_descriptor(descriptor: dict[str, Any]) -> bool:
        searchable = " ".join(
            str(descriptor.get(key, "")).lower()
            for key in ("name", "description", "execution_policy")
        )
        return not any(marker in searchable for marker in _PROHIBITED_MARKERS)

    def _required_modules(self, project: ResearchProjectSpec) -> tuple[str, ...]:
        if self._target_requested(project):
            return ("project_brief", _TARGET_MODULE, "independent_review", "research_report")
        return _BASELINE_MODULES

    @staticmethod
    def _target_requested(project: ResearchProjectSpec) -> bool:
        return project.domain == "disease_target_discovery" or "target_task_spec" in project.context

    def _check_baseline_available(self, project: ResearchProjectSpec) -> None:
        missing = set(self._required_modules(project)) - self.allowed_modules
        if missing:
            raise PlannerConfigurationError(
                f"safe research workflow modules are not registered: {sorted(missing)}"
            )
        required_count = len(self._required_modules(project))
        if required_count > project.max_work_items:
            raise PlannerConfigurationError(
                f"max_work_items={project.max_work_items} cannot fit the "
                f"{required_count}-item safe baseline"
            )

    def deterministic(self, project: ResearchProjectSpec, reason: str | None = None) -> ResearchPlan:
        """Build the auditable generic workflow used when Step is unavailable."""
        self._check_baseline_available(project)
        brief = WorkItemSpec(
            item_id="project_brief",
            title="Freeze the research question and completion contract",
            module="project_brief",
            objective="Preserve the original goal, constraints, success criteria and deliverables.",
            acceptance_criteria=["The original research goal is recorded without silent reframing."],
            output_contract=_output_contract(
                "ProjectBrief", question="string", deliverables="array", success_criteria="array"
            ),
        )
        literature = WorkItemSpec(
            item_id="literature_search",
            title="Retrieve source-indexed scientific literature",
            module="literature_search",
            objective="Collect citable records relevant to the frozen research question.",
            dependencies=[brief.item_id],
            inputs={"query": project.context.get("literature_query", project.goal.question)},
            acceptance_criteria=[
                "Every retrieved record has a stable source identifier.",
                "Retrieval hits are not represented as validated scientific claims.",
            ],
            output_contract=_output_contract(
                "LiteratureSearchResult",
                query="string",
                record_count="integer",
                source_ids="array",
                retrieval_hits_are_claims="boolean",
            ),
        )
        hypotheses = WorkItemSpec(
            item_id="hypothesis_generation",
            title="Generate source-aligned falsifiable hypotheses",
            module="hypothesis_generation",
            objective="Propose testable hypotheses without exceeding the retrieved source boundary.",
            dependencies=[literature.item_id],
            acceptance_criteria=[
                "Each accepted hypothesis cites only retrieved source identifiers.",
                "Each accepted hypothesis includes a falsification test and explicit assumptions.",
            ],
            output_contract=_output_contract(
                "HypothesisGenerationResult", hypothesis_count="integer", hypotheses="array"
            ),
        )
        scientific_items = [brief, literature, hypotheses]
        if self._target_requested(project):
            scientific_items = [brief, WorkItemSpec(
                item_id="target_discovery",
                title="Execute the bounded disease-target workflow",
                module="target_discovery",
                objective="Produce traceable candidate targets through the existing typed domain workflow.",
                dependencies=[brief.item_id],
                inputs={"target_task_spec": project.context.get("target_task_spec")},
                input_contract=_output_contract("TargetDiscoveryInput", target_task_spec="object"),
                acceptance_criteria=[
                    "The child workflow records its terminal status and durable outputs.",
                    "Evidence gaps and out-of-scope contexts remain explicit.",
                ],
                max_attempts=2,
                output_contract=_output_contract(
                    "TargetDiscoveryResult", child_run_id="string", terminal_status="string",
                    ranked_target_count="integer", target_card_count="integer",
                    experiment_plan_count="integer", deliverables_complete="boolean",
                    domain_activity_projection_complete="boolean",
                ),
            )]
        review = WorkItemSpec(
            item_id="independent_review",
            title="Independently review integrity and alignment",
            module="independent_review",
            objective="Verify durable artifacts, provenance and typed result boundaries before release.",
            dependencies=[item.item_id for item in scientific_items],
            acceptance_criteria=[
                "All registered artifacts receive deterministic integrity checks.",
                "Blocking failures remain visible and prevent an unqualified release.",
            ],
            output_contract=_output_contract(
                "IndependentReviewResult", assessment_count="integer", blocking_failures="array"
            ),
        )
        report = WorkItemSpec(
            item_id="research_report",
            title="Assemble the source-bounded research report",
            module="research_report",
            objective="Render executed work, artifacts, conclusions and unresolved gaps without adding new facts.",
            dependencies=[review.item_id],
            acceptance_criteria=[
                "The report is generated only from typed results and registered artifacts.",
                "Incomplete or unavailable work is stated as a gap.",
            ],
            output_contract=_output_contract(
                "ResearchReportResult", reported_items="integer", gap_count="integer"
            ),
        )
        backend = "deterministic:research-v3"
        if reason:
            backend += f" ({reason})"
        plan = ResearchPlan(
            project_id=project.project_id,
            items=[*scientific_items, review, report],
            planner_backend=backend,
            rationale=(
                "Use a source-grounded, typed workflow with an independent review gate and durable report."
            ),
        )
        self._validate(project, plan)
        return plan

    def _validate(
        self, project: ResearchProjectSpec, plan: ResearchPlan,
        canonical_template: ResearchPlan | None = None,
    ) -> None:
        if plan.project_id != project.project_id:
            raise ValueError("planner changed project_id")
        if len(plan.items) > project.max_work_items:
            raise ValueError("planner exceeded max_work_items")
        modules = [item.module for item in plan.items]
        unknown = set(modules) - self.allowed_modules
        if unknown:
            raise ValueError(f"planner selected non-whitelisted modules: {sorted(unknown)}")
        required = set(self._required_modules(project))
        missing = required - set(modules)
        if missing:
            raise ValueError(f"planner omitted required workflow modules: {sorted(missing)}")
        for control in self._required_modules(project):
            if modules.count(control) != 1:
                raise ValueError(f"planner must select {control} exactly once")
            if not next(item for item in plan.items if item.module == control).required:
                raise ValueError(f"planner cannot make required module optional: {control}")
        if not self._target_requested(project) and _TARGET_MODULE in modules:
            raise ValueError("target_discovery cannot run without target_task_spec")
        if any(item.output_contract is None for item in plan.items):
            raise ValueError("every work item must declare a typed output contract")

        by_module = {item.module: item for item in plan.items}
        review = by_module["independent_review"]
        report = by_module["research_report"]
        reviewed_ids = set(review.dependencies)
        expected_reviewed = {
            item.item_id for item in plan.items
            if item.module not in {"independent_review", "research_report"}
        }
        if not expected_reviewed.issubset(reviewed_ids):
            raise ValueError("independent_review does not cover every scientific work item")
        if review.item_id not in report.dependencies:
            raise ValueError("research_report must depend on independent_review")
        if canonical_template is not None:
            actual_by_module = {item.module: item for item in plan.items}
            for expected in canonical_template.items:
                actual = actual_by_module[expected.module]
                protected = (
                    "item_id", "required", "output_contract", "acceptance_criteria", "max_attempts",
                )
                changed = [name for name in protected if getattr(actual, name) != getattr(expected, name)]
                dependencies_valid = (
                    set(expected.dependencies).issubset(actual.dependencies)
                    if expected.module == "independent_review"
                    else actual.dependencies == expected.dependencies
                )
                if not dependencies_valid:
                    changed.append("dependencies")
                if changed:
                    raise ValueError(
                        f"planner changed protected safety fields for {expected.module}: {changed}"
                    )

    def create_plan(self, project: ResearchProjectSpec) -> ResearchPlan:
        self._check_baseline_available(project)
        if self.client is None:
            return self.deterministic(project, "Step API not configured")

        template = self.deterministic(project)
        system = (
            "You plan auditable life-science research. Return exactly one JSON object with only "
            "'items' and 'rationale'. Each item must satisfy the supplied WorkItemSpec schema. "
            "Use only registered typed modules and preserve every module in the required template. "
            "For a disease-target project, target_discovery is the bounded scientific workflow; do not "
            "duplicate its internal literature or omics stages at project level. The independent_review item must depend "
            "on every scientific work item and research_report must depend on independent_review. "
            "Never request shell, command execution, arbitrary code, dynamic scripts or unregistered tools. "
            "When evidence_strategy_patterns are provided, use them only as strategy hints for choosing "
            "evidence order and stop rules; they are never evidence for the current task and never justify "
            "changing a protected safety field. skill_hints list on-demand best-practice bundles; they are references for choosing and sequencing typed modules, never a license to add unregistered modules or free-form execution."
        )
        target_context = (
            project.context.get("target_task_spec", {}).get("context", {})
            if isinstance(project.context.get("target_task_spec"), dict) else {}
        )
        evidence_strategy_patterns: list[dict[str, Any]] = []
        if self.pattern_store is not None and isinstance(target_context, dict):
            availability = infer_data_availability(target_context)
            evidence_strategy_patterns = self.few_shot.build(
                disease=str(target_context.get("disease") or project.goal.question),
                tissue=target_context.get("tissue") if isinstance(target_context.get("tissue"), str) else None,
                cell_type=target_context.get("cell_type") if isinstance(target_context.get("cell_type"), str) else None,
                data_availability=availability,
            )
        skill_hints: list[dict[str, Any]] = []
        if isinstance(target_context, dict):
            from .paper_strategy import infer_data_availability as _infer_availability

            availability = _infer_availability(target_context)
            available_lanes = [lane for lane, available in (availability or {}).items() if available]
            skill_hints = self.skill_hints.build(
                lanes=available_lanes or None,
                scopes=["disease_target_discovery"],
                query=str(target_context.get("disease") or project.goal.question),
            )
        user = json.dumps({
            "project": {
                "project_id": project.project_id,
                "title": project.title,
                "domain": project.domain,
                "goal": project.goal.model_dump(mode="json"),
                "context_keys": sorted(project.context),
                "target_context": (project.context.get("target_task_spec", {}).get("context", {})
                                   if isinstance(project.context.get("target_task_spec"), dict) else {}),
            },
            "registered_capabilities": self.capabilities,
            "max_work_items": project.max_work_items,
            "evidence_strategy_patterns": evidence_strategy_patterns,
            "skill_hints": skill_hints,
            "required_template": {
                "items": [item.model_dump(mode="json") for item in template.items],
                "rationale": template.rationale,
            },
        }, ensure_ascii=False)
        try:
            raw = self.client.json_completion(system, user)
            payload = _PlannerPayload.model_validate(raw)
            backend = f"step:{self.client.model}"
            if evidence_strategy_patterns:
                backend += f"+pattern-fewshot:{len(evidence_strategy_patterns)}"
            if skill_hints:
                backend += f"+skills:{len(skill_hints)}"
            plan = ResearchPlan(
                project_id=project.project_id,
                items=payload.items,
                planner_backend=backend,
                rationale=payload.rationale,
                evidence_strategy_patterns=evidence_strategy_patterns,
            )
            self._validate(project, plan, canonical_template=template)
            return plan
        except (LLMUnavailable, ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.deterministic(project, exc.__class__.__name__)


__all__ = ["PlannerConfigurationError", "ResearchPlanner"]
