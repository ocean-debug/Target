"""Shared validation for resuming file-backed Agent runs."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from .candidate_policy import initial_candidate_genes
from .contracts import CONTRACT_VERSION, EvidenceItem, ExecutionPlan, TaskSpec, ToolResult


MergeCandidates = Callable[[list[str], ToolResult, int], list[str]]


def require_current_contract_for_resume(
    source_version: str | None,
    checkpoint: dict[str, Any] | None,
) -> None:
    """Prevent an unfinished legacy run from mixing persisted contract versions."""
    if source_version == CONTRACT_VERSION:
        return
    if checkpoint and checkpoint.get("terminal_status"):
        return
    raise ValueError(
        "legacy non-terminal runs cannot resume in place; start a derived 2.2.0 run"
    )


def load_validated_terminal_status(
    *, run_dir: Path, run_id: str, task_id: str,
    source_contract_version: str | None, checkpoint: dict[str, Any],
) -> dict[str, Any]:
    """Return an idempotent terminal status only when its durable witnesses agree."""
    path = run_dir / "status.json"
    if not path.exists():
        raise ValueError("missing provenance: terminal checkpoint exists without status.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("terminal checkpoint/status provenance mismatch: status must be an object")
    expected = {
        "contract_version": source_contract_version,
        "run_id": run_id,
        "task_id": task_id,
        "state": "terminal",
        "terminal_status": checkpoint.get("terminal_status"),
    }
    mismatches = {
        key: {"expected": value, "observed": payload.get(key)}
        for key, value in expected.items()
        if value is None or payload.get(key) != value
    }
    if mismatches:
        raise ValueError(f"terminal checkpoint/status provenance mismatch: {mismatches}")
    return payload


def restore_checkpoint_state(
    *,
    task: TaskSpec,
    plan: ExecutionPlan,
    checkpoint: dict[str, Any] | None,
    stored_results: list[ToolResult],
    stored_evidence: list[EvidenceItem],
    merge_candidates: MergeCandidates,
) -> tuple[set[str], list[str], int]:
    """Validate durable progress and rebuild derived state from authoritative records."""
    if checkpoint is None:
        return set(), initial_candidate_genes(task), 0

    tool_run_ids = [result.tool_run_id for result in stored_results]
    if len(tool_run_ids) != len(set(tool_run_ids)):
        raise ValueError("persisted ToolResult records contain duplicate tool_run_id values")
    evidence_ids = [item.evidence_id for item in stored_evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("persisted EvidenceItem records contain duplicate evidence_id values")

    raw_completed = checkpoint.get("completed_steps", [])
    if not isinstance(raw_completed, list) or any(not isinstance(item, str) for item in raw_completed):
        raise ValueError("checkpoint completed_steps must be a list of step IDs")
    completed_steps = set(raw_completed)
    if len(completed_steps) != len(raw_completed):
        raise ValueError("checkpoint completed_steps contains duplicate step IDs")

    by_id = {step.step_id: step for step in plan.steps}
    unknown = completed_steps - set(by_id)
    if unknown:
        raise ValueError(f"checkpoint references unknown completed steps: {sorted(unknown)}")
    for step_id in completed_steps:
        missing_dependencies = set(by_id[step_id].dependencies) - completed_steps
        if missing_dependencies:
            raise ValueError(
                f"checkpoint step {step_id} is missing completed dependencies: "
                f"{sorted(missing_dependencies)}"
            )

    required_results = Counter(
        by_id[step_id].tool for step_id in completed_steps if by_id[step_id].tool
    )
    stored_by_tool = Counter(result.tool_name for result in stored_results)
    orphan_result_tools = set(stored_by_tool) - set(required_results)
    if orphan_result_tools:
        raise ValueError(
            "persisted ToolResult records have no completed plan step: "
            f"{sorted(orphan_result_tools)}"
        )
    missing_results = {
        tool: count - stored_by_tool[tool]
        for tool, count in required_results.items()
        if stored_by_tool[tool] < count
    }
    if missing_results:
        raise ValueError(
            "checkpoint marks tool steps complete without matching ToolResult records: "
            f"{missing_results}"
        )

    raw_tool_calls = checkpoint.get("tool_calls", 0)
    if type(raw_tool_calls) is not int or raw_tool_calls < 0:  # bool is not a valid count
        raise ValueError("checkpoint tool_calls must be a non-negative integer")
    if raw_tool_calls != len(stored_results):
        raise ValueError(
            "checkpoint tool_calls does not match the number of persisted ToolResult records"
        )

    candidate_genes = initial_candidate_genes(task)
    for result in stored_results:
        candidate_genes = merge_candidates(
            candidate_genes,
            result,
            task.constraints.max_initial_candidates,
        )
    return completed_steps, candidate_genes, raw_tool_calls


__all__ = [
    "load_validated_terminal_status", "require_current_contract_for_resume",
    "restore_checkpoint_state",
]
