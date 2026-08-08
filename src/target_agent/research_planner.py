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
from .workflow_catalog import WorkflowCatalog, WorkflowTemplate
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
        paper_rag: Any | None = None,
        paper_top_k: int = 2,
        workflow_catalog: WorkflowCatalog | None = None,
    ):
        self.registry = registry
        self.client = client
        self.pattern_store = pattern_store
        self.few_shot = PlannerFewShotBuilder(
            pattern_store, few_shot_top_k, paper_rag=paper_rag, paper_top_k=paper_top_k,
        )
        self.skill_hints = SkillHintBuilder(skill_catalog, skill_hint_top_k)
        self.workflow_catalog = workflow_catalog

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

    def _template_for(self, project: ResearchProjectSpec) -> WorkflowTemplate | None:
        """Resolve the frozen workflow template for a project, failing closed on change."""
        if not project.workflow_template:
            return None
        if self.workflow_catalog is None:
            raise PlannerConfigurationError(
                "project uses a workflow template but no workflow catalog is configured"
            )
        template = self.workflow_catalog.get(project.workflow_template)
        if project.workflow_template_sha256 and project.workflow_template_sha256 != template.source_sha256:
            raise PlannerConfigurationError(
                f"workflow template {template.template_id} changed after project freeze"
            )
        return template

    def _required_modules(
        self,
        project: ResearchProjectSpec,
        template: WorkflowTemplate | None = None,
    ) -> tuple[str, ...]:
        if template is not None:
            return tuple(item.module for item in template.modules if item.required)
        if self._target_requested(project):
            return ("project_brief", _TARGET_MODULE, "independent_review", "research_report")
        return _BASELINE_MODULES

    @staticmethod
    def _target_requested(project: ResearchProjectSpec) -> bool:
        return project.domain == "disease_target_discovery" or "target_task_spec" in project.context

    @staticmethod
    def _template_allows_target(template: WorkflowTemplate | None) -> bool:
        return template is not None and any(
            item.module == _TARGET_MODULE for item in template.modules
        )

    def _template_allowed(self, template: WorkflowTemplate | None) -> set[str] | None:
        if template is None or self.workflow_catalog is None:
            return None
        return self.workflow_catalog.allowed_modules(template.template_id)

    def _check_baseline_available(
        self, project: ResearchProjectSpec, template: WorkflowTemplate | None = None,
    ) -> None:
        missing = set(self._required_modules(project, template)) - self.allowed_modules
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

    def deterministic(
        self, project: ResearchProjectSpec, reason: str | None = None,
    ) -> ResearchPlan:
        """Build the auditable workflow from the frozen template or the legacy default."""
        template = self._template_for(project)
        self._check_baseline_available(project, template)
        allowed = self._template_allowed(template)
        specs: dict[str, Any] = {}
        if template is not None and self.workflow_catalog is not None:
            specs = self.workflow_catalog.module_specs(template.template_id)

        def include(module: str) -> bool:
            if allowed is None:
                if module in {"literature_search", "hypothesis_generation"} and self._target_requested(project):
                    return False
                return True
            spec = specs.get(module)
            return spec is not None and spec.required

        def required(module: str, default: bool = True) -> bool:
            spec = specs.get(module)
            return spec.required if spec is not None else default

        def attempts(module: str) -> int:
            spec = specs.get(module)
            return spec.max_attempts if spec is not None else 1

        brief = WorkItemSpec(
            item_id="project_brief",
            title="Freeze the research question and completion contract",
            module="project_brief",
            objective="Preserve the original goal, constraints, success criteria and deliverables.",
            acceptance_criteria=["The original research goal is recorded without silent reframing."],
            output_contract=_output_contract(
                "ProjectBrief", question="string", deliverables="array", success_criteria="array"
            ),
            required=required("project_brief"),
        )
        items = [brief]
        literature: WorkItemSpec | None = None
        hypotheses: WorkItemSpec | None = None
        if include("literature_search"):
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
                required=required("literature_search"),
                max_attempts=attempts("literature_search"),
            )
            items.append(literature)
        if include("hypothesis_generation"):
            hypotheses = WorkItemSpec(
                item_id="hypothesis_generation",
                title="Generate source-aligned falsifiable hypotheses",
                module="hypothesis_generation",
                objective="Propose testable hypotheses without exceeding the retrieved source boundary.",
                dependencies=[literature.item_id if literature else brief.item_id],
                acceptance_criteria=[
                    "Each accepted hypothesis cites only retrieved source identifiers.",
                    "Each accepted hypothesis includes a falsification test and explicit assumptions.",
                ],
                output_contract=_output_contract(
                    "HypothesisGenerationResult", hypothesis_count="integer", hypotheses="array"
                ),
                required=required("hypothesis_generation"),
                max_attempts=attempts("hypothesis_generation"),
            )
            items.append(hypotheses)
        if (allowed is not None and _TARGET_MODULE in allowed) or (template is None and self._target_requested(project)):
            items.append(WorkItemSpec(
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
                max_attempts=attempts(_TARGET_MODULE),
                output_contract=_output_contract(
                    "TargetDiscoveryResult", child_run_id="string", terminal_status="string",
                    ranked_target_count="integer", target_card_count="integer",
                    experiment_plan_count="integer", deliverables_complete="boolean",
                    domain_activity_projection_complete="boolean",
                ),
                required=required(_TARGET_MODULE),
            ))
        review = WorkItemSpec(
            item_id="independent_review",
            title="Independently review integrity and alignment",
            module="independent_review",
            objective="Verify durable artifacts, provenance and typed result boundaries before release.",
            dependencies=[item.item_id for item in items],
            acceptance_criteria=[
                "All registered artifacts receive deterministic integrity checks.",
                "Blocking failures remain visible and prevent an unqualified release.",
            ],
            output_contract=_output_contract(
                "IndependentReviewResult", assessment_count="integer", blocking_failures="array"
            ),
            required=required("independent_review"),
            max_attempts=attempts("independent_review"),
        )
        items.append(review)
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
            required=required("research_report"),
            max_attempts=attempts("research_report"),
        )
        items.append(report)
        backend = "deterministic:research-v3"
        if reason:
            backend += f" ({reason})"
        plan = ResearchPlan(
            project_id=project.project_id,
            items=items,
            planner_backend=backend,
            rationale=(
                "Use a source-grounded, typed workflow with an independent review gate and durable report."
            ),
        )
        self._validate(project, plan, template=template)
        return plan

    def _validate(
        self, project: ResearchProjectSpec, plan: ResearchPlan,
        canonical_template: ResearchPlan | None = None,
        template: WorkflowTemplate | None = None,
    ) -> None:
        if plan.project_id != project.project_id:
            raise ValueError("planner changed project_id")
        if len(plan.items) > project.max_work_items:
            raise ValueError("planner exceeded max_work_items")
        modules = [item.module for item in plan.items]
        unknown = set(modules) - self.allowed_modules
        if unknown:
            raise ValueError(f"planner selected non-whitelisted modules: {sorted(unknown)}")
        template_allowed = self._template_allowed(template)
        if template_allowed is not None:
            outside = set(modules) - template_allowed
            if outside:
                raise ValueError(
                    f"planner selected modules outside workflow template: {sorted(outside)}"
                )
        required = set(self._required_modules(project, template))
        missing = required - set(modules)
        if missing:
            raise ValueError(f"planner omitted required workflow modules: {sorted(missing)}")
        for control in self._required_modules(project, template):
            if modules.count(control) != 1:
                raise ValueError(f"planner must select {control} exactly once")
            if not next(item for item in plan.items if item.module == control).required:
                raise ValueError(f"planner cannot make required module optional: {control}")
        if _TARGET_MODULE in modules and not (
            self._template_allows_target(template)
            or (template is None and self._target_requested(project))
        ):
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
        template = self._template_for(project)
        self._check_baseline_available(project, template)
        if self.client is None:
            return self.deterministic(project, "Step API not configured")

        canonical = self.deterministic(project)
        template_scope = ""
        if template is not None:
            template_scope = (
                f" You are executing workflow template '{template.template_id}': {template.description}. "
                f"Allowed modules are exactly {sorted(self._template_allowed(template) or [])}; "
                "do not add or drop modules outside this allowlist."
            )
            if self._template_allows_target(template):
                template_scope += (
                    " For a disease-target template, target_discovery is the bounded scientific "
                    "workflow; do not duplicate its internal literature or omics stages at project level."
                )
        system = (
            "You plan auditable life-science research. Return exactly one JSON object with only "
            "'items' and 'rationale'. Each item must satisfy the supplied WorkItemSpec schema. "
            "Use only registered typed modules and preserve every module in the required template. "
            "The independent_review item must depend "
            "on every scientific work item and research_report must depend on independent_review. "
            "Never request shell, command execution, arbitrary code, dynamic scripts or unregistered tools. "
            "When evidence_strategy_patterns are provided, use them only as strategy hints for choosing "
            "evidence order and stop rules; they are never evidence for the current task and never justify "
            "changing a protected safety field. skill_hints list on-demand best-practice bundles; they are references for choosing and sequencing typed modules, never a license to add unregistered modules or free-form execution."
            + template_scope
        )
        target_context = (
            project.context.get("target_task_spec", {}).get("context", {})
            if isinstance(project.context.get("target_task_spec"), dict) else {}
        )
        evidence_strategy_patterns: list[dict[str, Any]] = []
        paper_evidence: list[dict[str, Any]] = []
        availability = None
        if isinstance(target_context, dict):
            availability = infer_data_availability(target_context)
            if self.pattern_store is not None:
                evidence_strategy_patterns = self.few_shot.build(
                    disease=str(target_context.get("disease") or project.goal.question),
                    tissue=target_context.get("tissue") if isinstance(target_context.get("tissue"), str) else None,
                    cell_type=target_context.get("cell_type") if isinstance(target_context.get("cell_type"), str) else None,
                    data_availability=availability,
                )
            paper_evidence = self.few_shot.build_paper_evidence(
                disease=str(target_context.get("disease") or project.goal.question),
                tissue=target_context.get("tissue") if isinstance(target_context.get("tissue"), str) else None,
                cell_type=target_context.get("cell_type") if isinstance(target_context.get("cell_type"), str) else None,
                data_availability=availability,
            )
        skill_hints: list[dict[str, Any]] = []
        if isinstance(target_context, dict):
            from .paper_strategy import infer_data_availability as _infer_availability

            skill_availability = _infer_availability(target_context)
            available_lanes = [lane for lane, available in (skill_availability or {}).items() if available]
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
            "paper_evidence": paper_evidence,
            "skill_hints": skill_hints,
            "required_template": {
                "items": [item.model_dump(mode="json") for item in canonical.items],
                "rationale": canonical.rationale,
            },
            "workflow_template": (
                {"template_id": template.template_id, "description": template.description,
                 "allowed_modules": sorted(self._template_allowed(template) or [])}
                if template is not None else None
            ),
        }, ensure_ascii=False)
        try:
            raw = self.client.json_completion(system, user)
            payload = _PlannerPayload.model_validate(raw)
            backend = f"step:{self.client.model}"
            if evidence_strategy_patterns:
                backend += f"+pattern-fewshot:{len(evidence_strategy_patterns)}"
            if paper_evidence:
                backend += f"+paper-rag:{len(paper_evidence)}"
            if skill_hints:
                backend += f"+skills:{len(skill_hints)}"
            plan = ResearchPlan(
                project_id=project.project_id,
                items=payload.items,
                planner_backend=backend,
                rationale=payload.rationale,
                evidence_strategy_patterns=evidence_strategy_patterns,
                paper_evidence=paper_evidence,
            )
            self._validate(project, plan, canonical_template=canonical, template=template)
            return plan
        except (LLMUnavailable, ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.deterministic(project, exc.__class__.__name__)


__all__ = ["PlannerConfigurationError", "ResearchPlanner"]
