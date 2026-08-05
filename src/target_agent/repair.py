"""Bounded Reviewer-driven repair for transient read-only connector failures."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .contracts import EvidenceItem, ReviewerFinding, TaskSpec, ToolResult, ToolStatus
from .reviewer import Reviewer
from .settings import Settings
from .store import EvidenceStore
from .tools.base import ToolContext, ToolRegistry


REPAIRABLE_READ_ONLY_TOOLS = frozenset({
    "geo_search",
    "cellxgene_discovery",
    "open_targets",
    "europe_pmc_rag",
    "clinical_trials_gov",
})


TraceCallback = Callable[[str, str, dict[str, Any], list[str]], None]
MergeCandidates = Callable[[list[str], ToolResult, int], list[str]]


@dataclass
class RepairOutcome:
    results: list[ToolResult]
    evidence: list[EvidenceItem]
    findings: list[ReviewerFinding]
    candidate_genes: list[str]
    tool_calls: int
    actions: list[dict[str, Any]]


def _latest_failed_tools(results: list[ToolResult]) -> list[str]:
    latest = latest_tool_results(results)
    return sorted(
        result.tool_name for result in latest
        if result.tool_name in REPAIRABLE_READ_ONLY_TOOLS and result.status == ToolStatus.FAILED
    )


def latest_tool_results(results: list[ToolResult]) -> list[ToolResult]:
    """Return the final attempt for each tool while the store retains every attempt."""
    latest: dict[str, ToolResult] = {}
    for result in results:
        latest[result.tool_name] = result
    return list(latest.values())


def repair_transient_connector_failures(
    *,
    task: TaskSpec,
    run_id: str,
    store: EvidenceStore,
    registry: ToolRegistry,
    reviewer: Reviewer,
    cache_dir,
    settings: Settings,
    results: list[ToolResult],
    evidence: list[EvidenceItem],
    findings: list[ReviewerFinding],
    candidate_genes: list[str],
    tool_calls: int,
    merge_candidates: MergeCandidates,
    trace: TraceCallback,
) -> RepairOutcome:
    """Retry only transient, read-only connectors and re-run review after each round."""
    current_results = list(results)
    current_evidence = list(evidence)
    current_findings = list(findings)
    current_candidates = list(candidate_genes)
    actions: list[dict[str, Any]] = []
    if settings.cache_only:
        return RepairOutcome(
            current_results, current_evidence, current_findings, current_candidates, tool_calls, actions,
        )

    for repair_round in range(1, task.constraints.max_review_rounds + 1):
        failed_tools = _latest_failed_tools(current_results)
        if not failed_tools or tool_calls >= task.constraints.max_tool_calls:
            break
        attempted: list[str] = []
        outcomes: dict[str, str] = {}
        related_ids: list[str] = []
        for tool_name in failed_tools:
            if tool_calls >= task.constraints.max_tool_calls:
                break
            attempted.append(tool_name)
            trace("tool_call", "reviewer_repair", {
                "tool": tool_name, "repair_round": repair_round,
                "reason": "previous_read_only_connector_failure",
            }, [])
            execution = registry.get(tool_name).run(ToolContext(
                task=task,
                run_dir=store.run_dir,
                cache_dir=cache_dir,
                candidate_genes=current_candidates,
                prior_results=current_results,
                settings=settings,
            ))
            tool_calls += 1
            for item in execution.evidence:
                store.add_evidence(item)
                current_evidence.append(item)
            store.add_tool_result(execution.result)
            current_results.append(execution.result)
            current_candidates = merge_candidates(
                current_candidates, execution.result, task.constraints.max_initial_candidates,
            )
            outcomes[tool_name] = execution.result.status.value
            related_ids.extend([execution.result.tool_run_id, *execution.result.evidence_ids])
            trace("tool_result", "reviewer_repair", {
                "tool": tool_name,
                "repair_round": repair_round,
                "status": execution.result.status.value,
                "coverage_status": execution.result.coverage_status.value,
                "context_match_score": execution.result.context_match_score,
            }, [execution.result.tool_run_id, *execution.result.evidence_ids])

        if not attempted:
            break
        action = {
            "round": repair_round,
            "action": "retry_failed_read_only_connectors",
            "tools": attempted,
            "outcomes": outcomes,
        }
        actions.append(action)
        trace("replan", "reviewer_repair", action, related_ids)
        current_findings = reviewer.review(task, latest_tool_results(current_results), current_evidence)
        for finding in current_findings:
            store.add_finding(finding)
        trace("review", "reviewer_repair", {
            "round": repair_round + 1,
            "blocking": sum(row.severity == "blocking" for row in current_findings),
            "major": sum(row.severity == "major" for row in current_findings),
            "minor": sum(row.severity == "minor" for row in current_findings),
            "reviewer_backend": reviewer.last_backend,
        }, [row.finding_id for row in current_findings])

    return RepairOutcome(
        current_results, current_evidence, current_findings, current_candidates, tool_calls, actions,
    )


__all__ = [
    "REPAIRABLE_READ_ONLY_TOOLS", "RepairOutcome", "latest_tool_results",
    "repair_transient_connector_failures",
]
