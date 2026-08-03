"""Lightweight, typed and resumable Agent state machine."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .cards import build_cards
from .contracts import (
    CaseRecord, Claim, ClaimClass, ExecutionPlan, ReviewerFinding, TaskSpec,
    TerminalStatus, ToolResult, TraceEvent, new_id,
)
from .graphs import build_mechanistic_graph
from .llm import StepClient
from .planner import Planner
from .ranking import RankedTarget, rank_targets
from .reporting import build_disease_report, build_mch_report, write_report
from .reviewer import Reviewer
from .store import EvidenceStore
from .tools import ToolRegistry, default_registry
from .tools.base import ToolContext


class TargetDiscoveryRuntime:
    def __init__(
        self,
        runs_dir: Path | None = None,
        cache_dir: Path | None = None,
        registry: ToolRegistry | None = None,
        planner: Planner | None = None,
    ):
        root = Path(__file__).resolve().parents[2]
        self.runs_dir = runs_dir or Path(os.getenv("TARGET_AGENT_RUN_DIR", root / "runs"))
        self.cache_dir = cache_dir or Path(os.getenv("TARGET_AGENT_CACHE_DIR", root / "cache"))
        self.registry = registry or default_registry()
        self.planner = planner or Planner(StepClient.from_env())
        self.reviewer = Reviewer()

    def _trace(self, store: EvidenceStore, run_id: str, task: TaskSpec, event_type: str, state: str,
               detail: dict[str, Any] | None = None, related_ids: list[str] | None = None) -> None:
        store.add_trace(TraceEvent(
            run_id=run_id, task_id=task.task_id, event_type=event_type, state=state,
            detail=detail or {}, related_ids=related_ids or [],
        ))

    @staticmethod
    def _status(store: EvidenceStore, run_id: str, task: TaskSpec, state: str,
                terminal: TerminalStatus | None = None, detail: dict[str, Any] | None = None) -> None:
        store.save_json("status.json", {
            "contract_version": "2.0.0", "run_id": run_id, "task_id": task.task_id,
            "state": state, "terminal_status": terminal.value if terminal else None, "detail": detail or {},
        })

    @staticmethod
    def _serialize_ranked(ranked: list[RankedTarget], limit: int) -> list[dict[str, Any]]:
        return [
            {
                "rank": rank, "gene": item.gene, "scores": item.scores.model_dump(mode="json"),
                "decision": item.decision, "evidence_ids": item.evidence_ids,
                "supporting_ids": item.supporting_ids, "opposing_ids": item.opposing_ids,
                "safety_blockers": item.safety_blockers, "evidence_gaps": item.evidence_gaps,
                "matched_drugs": item.matched_drugs,
            }
            for rank, item in enumerate(ranked[:limit], start=1)
        ]

    def run(self, task: TaskSpec, run_id: str | None = None, resume: bool = False) -> dict[str, Any]:
        run_id = run_id or new_id("run")
        run_dir = self.runs_dir / run_id
        if run_dir.exists() and not resume:
            raise FileExistsError(f"run already exists: {run_id}; use resume=True")
        store = EvidenceStore(run_dir)
        checkpoint = store.load_checkpoint() if resume else None
        if checkpoint and checkpoint.get("terminal_status"):
            return json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        store.save_task(task)
        self._status(store, run_id, task, "intake")
        self._trace(store, run_id, task, "state_transition", "intake", {"resume": resume})

        plan = self._load_or_plan(store, task, checkpoint)
        self._trace(store, run_id, task, "plan", "planner", {
            "planner_backend": plan.planner_backend, "fallback_used": plan.fallback_used,
            "steps": [step.step_id for step in plan.steps],
        }, [plan.plan_id])
        completed_tools = set((checkpoint or {}).get("completed_tools", []))
        candidate_genes = list((checkpoint or {}).get("candidate_genes", task.candidate_genes))
        tool_calls = int((checkpoint or {}).get("tool_calls", 0))

        self._status(store, run_id, task, "tool_execution")
        for step in plan.steps:
            if not step.tool or step.tool in completed_tools:
                continue
            if tool_calls >= task.constraints.max_tool_calls:
                self._trace(store, run_id, task, "degradation", "tool_execution", {"reason": "tool_call_budget_exhausted"})
                break
            tool = self.registry.get(step.tool)
            self._trace(store, run_id, task, "tool_call", "tool_execution", {"tool": step.tool, "step_id": step.step_id})
            execution = tool.run(ToolContext(
                task=task, run_dir=run_dir, cache_dir=self.cache_dir, candidate_genes=candidate_genes,
            ))
            tool_calls += 1
            for item in execution.evidence:
                store.add_evidence(item)
            store.add_tool_result(execution.result)
            completed_tools.add(step.tool)
            self._trace(store, run_id, task, "tool_result", "tool_execution", {
                "tool": step.tool, "status": execution.result.status.value,
                "coverage_status": execution.result.coverage_status.value,
                "context_match_score": execution.result.context_match_score,
            }, [execution.result.tool_run_id, *execution.result.evidence_ids])
            if step.tool == "uc_omics_snapshot" and execution.result.outputs.get("candidates"):
                candidate_genes = [row["gene"] for row in execution.result.outputs["candidates"]]
            elif step.tool == "open_targets" and execution.result.outputs.get("top_genetic_candidates"):
                genetic_genes = [row["gene"] for row in execution.result.outputs["top_genetic_candidates"]]
                fused = candidate_genes[:12]
                fused.extend(gene for gene in genetic_genes if gene not in fused)
                candidate_genes = fused[: task.constraints.max_initial_candidates]
            checkpoint = {
                "stage": "tool_execution", "completed_tools": sorted(completed_tools),
                "candidate_genes": candidate_genes, "tool_calls": tool_calls,
            }
            store.checkpoint(checkpoint)
            self._trace(store, run_id, task, "checkpoint", "tool_execution", checkpoint)

            if execution.result.status.value == "out_of_scope" and step.tool in {"uc_omics_snapshot", "mch_causal_gold"}:
                break

        results = store.tool_results()
        evidence = store.evidences()
        store.assert_referential_integrity()

        self._status(store, run_id, task, "reviewer")
        findings = self.reviewer.review(task, results, evidence)
        for finding in findings:
            store.add_finding(finding)
        self._trace(store, run_id, task, "review", "reviewer", {
            "round": 1, "blocking": sum(f.severity == "blocking" for f in findings),
            "major": sum(f.severity == "major" for f in findings),
            "minor": sum(f.severity == "minor" for f in findings),
        }, [f.finding_id for f in findings])

        # A second audited reviewer round records that no safe automatic repair exists.
        # External evidence gaps are never patched by fabricated evidence or code mutation.
        if any(f.severity in {"blocking", "major"} for f in findings):
            self._trace(store, run_id, task, "replan", "reviewer", {
                "round": 2, "action": "retain gaps; no automatic code/training/publication mutation",
            })

        status = self._terminal_status(findings, results)
        ranked_payload: list[dict[str, Any]] = []
        cards = []
        final_claims: list[Claim] = []
        if task.task_type == "disease_to_target" and candidate_genes:
            ranked = rank_targets(candidate_genes, evidence, results)
            ranked_payload = self._serialize_ranked(ranked, task.constraints.max_ranked_targets)
            cards = build_cards(task, ranked)
            store.save_json("ranked_targets.json", ranked_payload)
            store.save_cards(cards)
            graph = build_mechanistic_graph(task, evidence, [row["gene"] for row in ranked_payload])
            store.save_json("mechanistic_evidence_graph.json", graph)
            for row in ranked_payload:
                if row["evidence_ids"]:
                    claim = Claim(
                        claim_class=ClaimClass.INFERRED,
                        statement=f"{row['gene']} is ranked {row['rank']} for prioritization; this is not a success probability.",
                        evidence_ids=row["evidence_ids"],
                        synthesis_rationale="Transparent six-dimensional ranking with context multipliers and independent blocker retention.",
                    )
                    store.add_claim(claim)
                    final_claims.append(claim)
            self._trace(store, run_id, task, "ranking", "ranking", {
                "ranked_targets": len(ranked_payload), "target_cards": len(cards),
                "highlighted_targets": [row["gene"] for row in ranked_payload[:3]],
            }, [card.target_card_id for card in cards])

        if task.task_type == "disease_to_target":
            report_payload, markdown = build_disease_report(task, status, ranked_payload, cards, findings, results)
        else:
            mch_result = next((result for result in results if result.tool_name == "mch_causal_gold"), None)
            report_payload, markdown = build_mch_report(task, status, mch_result, findings)
            if mch_result and mch_result.outputs.get("graph"):
                store.save_json("causal_graph.json", mch_result.outputs["graph"])
        write_report(run_dir, report_payload, markdown)
        self._trace(store, run_id, task, "report", "report", {"status": status.value}, [claim.claim_id for claim in final_claims])

        case = CaseRecord(
            run_id=run_id, task_spec=task, plan=plan,
            tool_run_ids=[result.tool_run_id for result in results],
            finding_ids=[finding.finding_id for finding in findings],
            revision_history=[{"round": 1, "findings": len(findings)}, {"round": 2, "action": "gaps retained"}] if findings else [],
            final_status=status, final_claim_ids=[claim.claim_id for claim in final_claims],
            scientific_review="pending", promotion_eligible=False,
        )
        store.save_case(case)
        final_checkpoint = {
            "stage": "terminal", "completed_tools": sorted(completed_tools), "candidate_genes": candidate_genes,
            "tool_calls": tool_calls, "terminal_status": status.value,
        }
        store.checkpoint(final_checkpoint)
        self._status(store, run_id, task, "terminal", status, {
            "report": "report.md", "ranked_targets": len(ranked_payload), "target_cards": len(cards),
            "tool_calls": tool_calls,
        })
        return json.loads((run_dir / "status.json").read_text(encoding="utf-8"))

    def _load_or_plan(self, store: EvidenceStore, task: TaskSpec, checkpoint: dict[str, Any] | None) -> ExecutionPlan:
        plan_path = store.run_dir / "execution_plan.json"
        if checkpoint and plan_path.exists():
            return ExecutionPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
        plan = self.planner.create_plan(task)
        store.save_plan(plan)
        return plan

    @staticmethod
    def _terminal_status(findings: list[ReviewerFinding], results: list[ToolResult]) -> TerminalStatus:
        blocking = [f for f in findings if f.severity == "blocking"]
        if any(f.category == "missing_provenance" for f in blocking):
            return TerminalStatus.FAILED
        if any(f.category == "coverage_gap" for f in blocking):
            return TerminalStatus.NEEDS_INPUT
        if any(result.status.value == "failed" for result in results) or any(f.severity == "major" for f in findings):
            return TerminalStatus.COMPLETED_WITH_GAPS
        return TerminalStatus.COMPLETED
