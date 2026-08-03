"""LLM-assisted planner over the live typed registry with generic fallbacks."""
from __future__ import annotations

import json

from pydantic import ValidationError

from .contracts import ExecutionPlan, PlanStep, TaskSpec
from .llm import LLMUnavailable, StepClient
from .tools.base import ToolRegistry


DISEASE_STEPS = [
    PlanStep(step_id="scope", name="Normalize disease and biological context", tool="disease_resolver", success_criteria=["disease label and search synonyms are explicit"], stop_conditions=["missing disease"]),
    PlanStep(step_id="geo_search", name="Discover disease-matched GEO Series", tool="geo_search", dependencies=["scope"], success_criteria=["ranked dataset candidates include stable accessions"], degradation_conditions=["no GEO Series found"]),
    PlanStep(step_id="geo_audit", name="Audit GEO metadata and biological replication", tool="geo_metadata_audit", dependencies=["geo_search"], success_criteria=["case/control groups pass deterministic gates"], degradation_conditions=["metadata confidence or replication below threshold"]),
    PlanStep(step_id="recipe", name="Instantiate an allowlisted omics recipe", tool="omics_recipe_builder", dependencies=["geo_audit"], success_criteria=["backend matches matrix type"], stop_conditions=["unsupported data format"]),
    PlanStep(step_id="bulk", name="Run processed bulk expression analysis", tool="bulk_expression_analysis", dependencies=["recipe"], success_criteria=["QC, full differential table and provenance are retained"], degradation_conditions=["no eligible processed count matrix"]),
    PlanStep(step_id="census", name="Discover versioned CELLxGENE disease data", tool="cellxgene_discovery", dependencies=["scope"], success_criteria=["query size is checked before expression retrieval"], degradation_conditions=["no exact disease/tissue match"]),
    PlanStep(step_id="single_cell", name="Validate and analyze selected standard single-cell input", tool="single_cell_analysis", dependencies=["census"], success_criteria=["donor-level pseudobulk gate is satisfied"], degradation_conditions=["dataset not explicitly selected or metadata incomplete"]),
    PlanStep(step_id="pathway", name="Run full-rank pathway enrichment", tool="pathway_enrichment", dependencies=["bulk"], success_criteria=["GSEA seed, library date and full results are stored"], degradation_conditions=["no ranked differential statistic"]),
    PlanStep(step_id="omics_candidates", name="Consolidate validated omics candidates", tool="omics_candidate_extraction", dependencies=["bulk", "single_cell"], success_criteria=["candidate genes originate in typed tool outputs"]),
    PlanStep(step_id="genetics", name="Resolve disease and retrieve human genetic associations", tool="open_targets", dependencies=["scope"], success_criteria=["association records include stable disease and target IDs"], degradation_conditions=["network or disease resolution unavailable"]),
    PlanStep(step_id="literature", name="Retrieve source-grounded literature claims", tool="europe_pmc_rag", dependencies=["omics_candidates", "genetics"], success_criteria=["every claim has a literal source span"], degradation_conditions=["no span-valid claim"]),
    PlanStep(step_id="review", name="Review provenance, context, conflicts and causal language", dependencies=["bulk", "single_cell", "pathway", "genetics", "literature"], success_criteria=["no blocking finding remains"], degradation_conditions=["major evidence gaps remain after two rounds"]),
    PlanStep(step_id="ranking", name="Rank candidates while retaining blockers", dependencies=["review"], success_criteria=["score is not represented as probability"]),
    PlanStep(step_id="report", name="Generate TargetCards and traceable report", dependencies=["ranking"], success_criteria=["all numbers originate in the Evidence Store"]),
]

MCH_STEPS = [
    PlanStep(step_id="scope", name="Validate MCH-only gold-sample scope", success_criteria=["trait equals MCH"], stop_conditions=["non-MCH trait"]),
    PlanStep(step_id="mch", name="Validate paper and extended causal-model reproductions", tool="mch_causal_gold", dependencies=["scope"], success_criteria=["paper 43/59 and extension 94/147 remain separate"]),
    PlanStep(step_id="review", name="Review causal scope and numeric consistency", dependencies=["mch"]),
    PlanStep(step_id="report", name="Generate gold-sample report", dependencies=["review"]),
]


class Planner:
    def __init__(self, client: StepClient | None = None, registry: ToolRegistry | None = None):
        self.client = client
        self.registry = registry

    @property
    def allowed_tools(self) -> set[str]:
        if self.registry:
            return set(self.registry.names)
        return {step.tool for step in DISEASE_STEPS + MCH_STEPS if step.tool}

    def deterministic(self, task: TaskSpec, reason: str | None = None) -> ExecutionPlan:
        steps = DISEASE_STEPS if task.task_type == "disease_to_target" else MCH_STEPS
        if task.task_type == "disease_to_target":
            modes = set(task.constraints.dataset_selection.omics_modes)
            excluded_steps: set[str] = set()
            if "geo_bulk" not in modes:
                excluded_steps.update({"geo_search", "geo_audit", "recipe", "bulk", "pathway"})
            if "cellxgene" not in modes:
                excluded_steps.add("census")
            if "cellxgene" not in modes and "local_single_cell" not in modes and not task.omics_inputs:
                excluded_steps.add("single_cell")
            steps = [step for step in steps if step.step_id not in excluded_steps]
        available = self.allowed_tools
        selected = [step.model_copy(deep=True) for step in steps if not step.tool or step.tool in available]
        selected_ids = {step.step_id for step in selected}
        for step in selected:
            step.dependencies = [item for item in step.dependencies if item in selected_ids]
        return ExecutionPlan(
            task_id=task.task_id,
            planner_backend="deterministic:v2.1" if not reason else f"deterministic:v2.1 ({reason})",
            steps=selected, fallback_used=bool(reason),
        )

    def _validate(self, task: TaskSpec, plan: ExecutionPlan) -> None:
        if len([step for step in plan.steps if step.tool]) > task.constraints.max_tool_calls:
            raise ValueError("planner exceeded tool-call budget")
        ids = [step.step_id for step in plan.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("planner emitted duplicate step IDs")
        known = set(ids)
        for step in plan.steps:
            if step.tool and step.tool not in self.allowed_tools:
                raise ValueError(f"planner selected a non-whitelisted tool: {step.tool}")
            if any(dep not in known or dep == step.step_id for dep in step.dependencies):
                raise ValueError(f"planner emitted an invalid dependency for {step.step_id}")
        visiting: set[str] = set()
        visited: set[str] = set()
        by_id = {step.step_id: step for step in plan.steps}

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise ValueError("planner emitted a dependency cycle")
            if step_id in visited:
                return
            visiting.add(step_id)
            for dependency in by_id[step_id].dependencies:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in ids:
            visit(step_id)
        if task.task_type == "disease_to_target":
            required = {"disease_resolver", "omics_candidate_extraction"}
            modes = set(task.constraints.dataset_selection.omics_modes)
            if "geo_bulk" in modes:
                required.update({"geo_search", "geo_metadata_audit", "omics_recipe_builder"})
            if "cellxgene" in modes:
                required.add("cellxgene_discovery")
            if "cellxgene" in modes or "local_single_cell" in modes or task.omics_inputs:
                required.add("single_cell_analysis")
        else:
            required = {"mch_causal_gold"}
        enabled_required = required & self.allowed_tools
        planned = {step.tool for step in plan.steps if step.tool}
        if not enabled_required.issubset(planned):
            raise ValueError("planner omitted required generic workflow tools")

    def create_plan(self, task: TaskSpec) -> ExecutionPlan:
        if not self.client:
            return self.deterministic(task, "Step API not configured")
        template = self.deterministic(task)
        capabilities = self.registry.public_capabilities() if self.registry else [{"tool_id": name} for name in sorted(self.allowed_tools)]
        system = (
            "You are a life-science workflow planner. Return only an ExecutionPlan-compatible JSON object. "
            "Use only the supplied typed tool capabilities. Preserve the generic dataset discovery, metadata audit, "
            "review and provenance steps. Never generate shell commands or analysis code."
        )
        user = json.dumps({
            "task": task.model_dump(mode="json"), "tool_capabilities": capabilities,
            "required_template": template.model_dump(mode="json"),
            "limits": {"tool_calls": task.constraints.max_tool_calls, "review_rounds": task.constraints.max_review_rounds},
        }, ensure_ascii=False)
        last_error: Exception | None = None
        call_system, call_user = system, user
        for attempt in range(2):
            raw: dict = {}
            try:
                raw = self.client.json_completion(call_system, call_user)
                backend = f"step:{self.client.model}" + (":repaired" if attempt else "")
                candidate = dict(raw)
                candidate.update({"task_id": task.task_id, "planner_backend": backend, "fallback_used": False})
                plan = ExecutionPlan.model_validate(candidate)
                self._validate(task, plan)
                if self.client.last_request_meta is not None:
                    self.client.last_request_meta.update({
                        "structured_attempts": attempt + 1,
                        "repair_used": bool(attempt),
                    })
                return plan
            except LLMUnavailable as exc:
                last_error = exc
                break
            except (ValidationError, ValueError, json.JSONDecodeError, TypeError) as exc:
                last_error = exc
                if attempt:
                    break
                errors = (
                    exc.errors(include_url=False, include_input=False)
                    if isinstance(exc, ValidationError)
                    else [{"type": exc.__class__.__name__, "message": str(exc)}]
                )
                call_system = (
                    "Repair an invalid life-science ExecutionPlan. Return only one JSON object that exactly follows "
                    "the supplied valid template structure. Keep every required tool and valid dependency. "
                    "Do not add fields, prose, shell commands or analysis code."
                )
                call_user = json.dumps({
                    "task": task.model_dump(mode="json"),
                    "invalid_output": raw,
                    "validation_errors": errors,
                    "required_template": template.model_dump(mode="json"),
                }, ensure_ascii=False)
        return self.deterministic(task, last_error.__class__.__name__ if last_error else "unknown planner error")
