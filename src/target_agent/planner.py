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
    PlanStep(step_id="trials", name="Retrieve gene-named clinical trial registry records", tool="clinical_trials_gov", dependencies=["genetics"], success_criteria=["every claim names the gene in the intervention or title text"], degradation_conditions=["no gene-named registry record"]),
    PlanStep(step_id="literature", name="Retrieve source-grounded literature claims", tool="europe_pmc_rag", dependencies=["omics_candidates", "genetics"], success_criteria=["every claim has a literal source span"], degradation_conditions=["no span-valid claim"]),
    PlanStep(step_id="review", name="Review provenance, context, conflicts and causal language", dependencies=["bulk", "single_cell", "pathway", "genetics", "trials", "literature"], success_criteria=["no blocking finding remains"], degradation_conditions=["major evidence gaps remain after two rounds"]),
    PlanStep(step_id="ranking", name="Rank candidates while retaining blockers", dependencies=["review"], success_criteria=["score is not represented as probability"]),
    PlanStep(step_id="report", name="Generate TargetCards and traceable report", dependencies=["ranking"], success_criteria=["all numbers originate in the Evidence Store"]),
]

GENETICS_INPUT_STEPS = [
    PlanStep(
        step_id="genetics_input_audit",
        name="Validate and normalize controlled genetics inputs",
        tool="genetics_input_audit",
        dependencies=["scope"],
        success_criteria=["checksums, genome builds, alleles and tabular contracts pass deterministic QC"],
        stop_conditions=["no genetics asset passes input QC"],
    ),
    PlanStep(
        step_id="fine_mapping_audit",
        name="Audit fine-mapping credible sets and LD provenance",
        tool="fine_mapping_audit",
        dependencies=["genetics_input_audit"],
        success_criteria=["eligible credible sets have matched LD, valid signal-posterior mass and GWAS overlap"],
        degradation_conditions=["no fine-mapping result was supplied or no credible set passes QC"],
    ),
    PlanStep(
        step_id="eqtl_colocalization_audit",
        name="Audit eQTL colocalization and tissue context",
        tool="eqtl_colocalization_audit",
        dependencies=["fine_mapping_audit"],
        success_criteria=["formal links pass regional overlap, allele, posterior, sensitivity and context gates"],
        degradation_conditions=["no colocalization result was supplied or all links fail a formal gate"],
    ),
    PlanStep(
        step_id="genetics_candidate_extraction",
        name="Extract only formally supported locus-to-gene hypotheses",
        tool="genetics_candidate_extraction",
        dependencies=["eqtl_colocalization_audit"],
        success_criteria=["every emitted gene is linked to typed, QC-passing statistical evidence"],
        degradation_conditions=["GWAS loci remain unresolved instead of being assigned to nearest genes"],
    ),
]

GENETICS_CHAIN = (
    ("genetics_input_audit", "genetics_input_audit", "scope"),
    ("fine_mapping_audit", "fine_mapping_audit", "genetics_input_audit"),
    ("eqtl_colocalization_audit", "eqtl_colocalization_audit", "fine_mapping_audit"),
    ("genetics_candidate_extraction", "genetics_candidate_extraction", "eqtl_colocalization_audit"),
)

GWAS_STEPS = [
    PlanStep(step_id="scope", name="Normalize disease and locus context", tool="disease_resolver", success_criteria=["disease, build, ancestry and locus context are explicit"], stop_conditions=["missing disease or genetics input"]),
    *GENETICS_INPUT_STEPS,
    PlanStep(step_id="genetics", name="Retrieve independent disease-level target evidence", tool="open_targets", dependencies=["genetics_candidate_extraction"], success_criteria=["association records include stable disease and target IDs"], degradation_conditions=["network or disease resolution unavailable"]),
    PlanStep(step_id="trials", name="Retrieve gene-named clinical trial registry records", tool="clinical_trials_gov", dependencies=["genetics"], success_criteria=["every claim names the gene in the intervention or title text"], degradation_conditions=["no gene-named registry record"]),
    PlanStep(step_id="literature", name="Retrieve source-grounded literature claims", tool="europe_pmc_rag", dependencies=["genetics_candidate_extraction", "genetics"], success_criteria=["every claim has a literal source span"], degradation_conditions=["no span-valid claim"]),
    PlanStep(step_id="review", name="Review provenance, context, conflicts and causal language", dependencies=["genetics_candidate_extraction", "genetics", "trials", "literature"], success_criteria=["no blocking finding remains"], degradation_conditions=["major evidence gaps remain after two rounds"]),
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
        return {step.tool for step in DISEASE_STEPS + GENETICS_INPUT_STEPS + GWAS_STEPS + MCH_STEPS if step.tool}

    def deterministic(self, task: TaskSpec, reason: str | None = None) -> ExecutionPlan:
        if task.task_type == "disease_to_target":
            steps = list(DISEASE_STEPS)
            if task.genetics_inputs:
                steps = [steps[0], *GENETICS_INPUT_STEPS, *steps[1:]]
        elif task.task_type == "gwas_locus_to_target":
            steps = list(GWAS_STEPS)
        else:
            steps = list(MCH_STEPS)
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
        if task.genetics_inputs or task.task_type == "gwas_locus_to_target":
            missing = {tool for _, tool, _ in GENETICS_CHAIN} - available
            if missing:
                raise ValueError(f"required genetics workflow tools are unavailable: {sorted(missing)}")
        selected = [step.model_copy(deep=True) for step in steps if not step.tool or step.tool in available]
        if task.genetics_inputs and task.task_type == "disease_to_target":
            by_id = {step.step_id: step for step in selected}
            for step_id in ("genetics", "review"):
                if step_id in by_id and "genetics_candidate_extraction" not in by_id[step_id].dependencies:
                    by_id[step_id].dependencies.append("genetics_candidate_extraction")
        selected_ids = {step.step_id for step in selected}
        for step in selected:
            step.dependencies = [item for item in step.dependencies if item in selected_ids]
        return ExecutionPlan(
            task_id=task.task_id,
            planner_backend="deterministic:v2.2" if not reason else f"deterministic:v2.2 ({reason})",
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
        genetics_required = bool(task.genetics_inputs) or task.task_type == "gwas_locus_to_target"
        genetics_tools = {tool for _, tool, _ in GENETICS_CHAIN}
        if genetics_required:
            for step_id, tool, dependency in GENETICS_CHAIN:
                step = by_id.get(step_id)
                if step is None or step.tool != tool or dependency not in step.dependencies:
                    raise ValueError("planner omitted or rewired the required genetics workflow chain")
        elif any(step.tool in genetics_tools for step in plan.steps):
            raise ValueError("planner selected genetics input tools without genetics_inputs")
        if task.task_type == "disease_to_target":
            required = {"disease_resolver", "omics_candidate_extraction"}
            modes = set(task.constraints.dataset_selection.omics_modes)
            if "geo_bulk" in modes:
                required.update({"geo_search", "geo_metadata_audit", "omics_recipe_builder"})
            if "cellxgene" in modes:
                required.add("cellxgene_discovery")
            if "cellxgene" in modes or "local_single_cell" in modes or task.omics_inputs:
                required.add("single_cell_analysis")
            if genetics_required:
                required.update(genetics_tools)
        elif task.task_type == "gwas_locus_to_target":
            required = {"disease_resolver", *genetics_tools}
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
