"""LLM-assisted planner with deterministic disease/MCH fallbacks."""
from __future__ import annotations

import json

from pydantic import ValidationError

from .contracts import ExecutionPlan, PlanStep, TaskSpec
from .llm import LLMUnavailable, StepClient


DISEASE_STEPS = [
    PlanStep(step_id="scope", name="Validate disease and biological context", success_criteria=["disease is normalized", "coverage boundary is explicit"], stop_conditions=["unsupported disease with no public input data"]),
    PlanStep(step_id="omics", name="Load disease-context omics candidates", tool="uc_omics_snapshot", dependencies=["scope"], success_criteria=["1-20 candidates with dataset provenance"], degradation_conditions=["disease or tissue is not covered"]),
    PlanStep(step_id="genetics", name="Retrieve human genetic associations", tool="open_targets", dependencies=["scope"], success_criteria=["association records include Open Targets IDs"], degradation_conditions=["network or API unavailable"]),
    PlanStep(step_id="literature", name="Retrieve and extract source-grounded literature claims", tool="europe_pmc_rag", dependencies=["omics"], success_criteria=["every claim has a literal source span"], degradation_conditions=["no extractable chunk supports a candidate"]),
    PlanStep(step_id="observed_perturbation", name="Query measured primary T-cell perturbations", tool="observed_tcell_perturbation", dependencies=["omics"], success_criteria=["coverage and assay context are explicit"]),
    PlanStep(step_id="predicted_perturbation", name="Check DeltaFactor prediction coverage", tool="deltafactor", dependencies=["omics"], success_criteria=["K562 predictions remain exploratory for UC"], degradation_conditions=["context_match_score below 0.5"]),
    PlanStep(step_id="mechanism", name="Assemble mechanistic evidence graph", dependencies=["literature", "observed_perturbation", "predicted_perturbation"], success_criteria=["edge class distinguishes observed, predicted and inferred"]),
    PlanStep(step_id="review", name="Review provenance, context, conflicts and causal language", dependencies=["genetics", "literature", "mechanism"], success_criteria=["no blocking finding remains"], degradation_conditions=["major evidence gap remains after two rounds"]),
    PlanStep(step_id="ranking", name="Rank candidates and retain blockers", dependencies=["review"], success_criteria=["10 ranked candidates; score is not a probability"]),
    PlanStep(step_id="report", name="Generate 5 TargetCards and traceable report", dependencies=["ranking"], success_criteria=["3 highlighted targets; all numbers originate in the store"]),
]

MCH_STEPS = [
    PlanStep(step_id="scope", name="Validate MCH-only gold-sample scope", success_criteria=["trait equals MCH"], stop_conditions=["non-MCH trait"]),
    PlanStep(step_id="mch", name="Validate paper and extended causal-model reproductions", tool="mch_causal_gold", dependencies=["scope"], success_criteria=["paper 43/59 and extension 94/147 are separately labelled", "Fig.3a and robustness checks are present"]),
    PlanStep(step_id="review", name="Review causal scope and numeric consistency", dependencies=["mch"], success_criteria=["no fixed MCH graph for other traits"]),
    PlanStep(step_id="report", name="Generate gold-sample report", dependencies=["review"], success_criteria=["K562 and MCH limitations are explicit"]),
]


class Planner:
    def __init__(self, client: StepClient | None = None):
        self.client = client

    def deterministic(self, task: TaskSpec, reason: str | None = None) -> ExecutionPlan:
        steps = DISEASE_STEPS if task.task_type == "disease_to_target" else MCH_STEPS
        return ExecutionPlan(
            task_id=task.task_id,
            planner_backend="deterministic:v2" if not reason else f"deterministic:v2 ({reason})",
            steps=[step.model_copy(deep=True) for step in steps],
            fallback_used=bool(reason),
        )

    def create_plan(self, task: TaskSpec) -> ExecutionPlan:
        if not self.client:
            return self.deterministic(task, "Step API not configured")
        system = (
            "You are a life-science workflow planner. Return only an ExecutionPlan-compatible JSON object. "
            "Use only these tools: uc_omics_snapshot, open_targets, europe_pmc_rag, "
            "observed_tcell_perturbation, deltafactor, mch_causal_gold. Never remove provenance, "
            "coverage, context or reviewer steps. Maximum 30 tool calls and two review rounds."
        )
        try:
            raw = self.client.json_completion(system, task.model_dump_json())
            raw.update({"task_id": task.task_id, "planner_backend": f"step:{self.client.model}", "fallback_used": False})
            plan = ExecutionPlan.model_validate(raw)
            allowed = {step.tool for step in DISEASE_STEPS + MCH_STEPS}
            if any(step.tool not in allowed for step in plan.steps):
                raise ValueError("planner selected a non-whitelisted tool")
            return plan
        except (LLMUnavailable, ValidationError, ValueError, json.JSONDecodeError) as exc:
            return self.deterministic(task, exc.__class__.__name__)

