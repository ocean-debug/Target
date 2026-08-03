"""Export JSON Schemas from the canonical Pydantic 2.0 models."""
from __future__ import annotations

import json
from pathlib import Path

from .contracts import (
    AnalysisRecipe, CaseRecord, CausalGraph, Claim, DatasetCandidate,
    DatasetSelectionConstraint, EvidenceItem, ExecutionPlan, ExperimentPlan,
    OmicsResult, ReviewerFinding, TargetCard, TaskSpec, ToolDescriptor, ToolResult,
    TraceEvent,
)


MODELS = {
    "task_spec": TaskSpec,
    "execution_plan": ExecutionPlan,
    "tool_result": ToolResult,
    "evidence_item": EvidenceItem,
    "claim": Claim,
    "reviewer_finding": ReviewerFinding,
    "causal_graph": CausalGraph,
    "experiment_plan": ExperimentPlan,
    "target_card": TargetCard,
    "trace_event": TraceEvent,
    "case_record": CaseRecord,
    "dataset_candidate": DatasetCandidate,
    "dataset_selection_constraint": DatasetSelectionConstraint,
    "analysis_recipe": AnalysisRecipe,
    "omics_result": OmicsResult,
    "tool_descriptor": ToolDescriptor,
}


def export_schemas(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = {f"{name}.schema.json" for name in MODELS}
    for stale in output_dir.glob("*.schema.json"):
        if stale.name not in expected:
            stale.unlink()
    written = []
    for name, model in MODELS.items():
        path = output_dir / f"{name}.schema.json"
        path.write_text(json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    for path in export_schemas(root / "schemas"):
        print(path)


if __name__ == "__main__":
    main()
