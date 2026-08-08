"""Typed candidate-bound evidence dependencies (P0.3).

Candidate-consuming evidence lanes (literature, genetics, drug/safety,
perturbation, trials) declare their dependence on the candidate universe in
the plan contract. The LangGraph runtime stamps each candidate-bound result
with a step_id + candidate digest, reuses only digest-matched persisted
results on resume, supersedes stale attempts and filters superseded evidence
out of review and ranking.
"""
from __future__ import annotations

import json

import pytest

from target_agent.contracts import (
    ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, ExecutionPlan,
    PlanStep, SourceLocator, Stance, TaskContext, TaskSpec, ToolCapability,
    ToolResult, ToolStatus, new_id,
)
from target_agent.planner import Planner
from target_agent.runtime_langgraph import (
    CANDIDATE_BOUND_OUTPUT_KEY, LangGraphRuntime, candidate_universe_digest,
)
from target_agent.store import EvidenceStore
from target_agent.tools.base import ScientificTool, ToolContext, ToolExecution, ToolRegistry

def _task() -> TaskSpec:
    return TaskSpec(
        task_id="task-typed-deps",
        task_type="disease_to_target",
        question="Find traceable UC targets",
        context=TaskContext(
            disease="ulcerative colitis",
            disease_id="MONDO_0005101",
            tissue="rectum",
            cell_type="T cell",
            desired_phenotype="restore state",
        ),
    )


def _jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


class FakeOmicsCandidates(ScientificTool):
    """Deterministic candidate producer with per-gene evidence."""

    name = "omics_candidate_extraction"
    version = "test"

    def run(self, context: ToolContext) -> ToolExecution:
        run_id = new_id("tool")
        genes = ["GENE1", "GENE2", "GENE3"]
        evidence = [
            EvidenceItem(
                tool_run_id=run_id, gene_symbol=gene, claim_class=ClaimClass.OBSERVED,
                statement=f"Fixture omics evidence for {gene}.",
                source=SourceLocator(uri="https://geo.test/fixture", source_id=f"geo-{gene}",
                                     chunk_id=f"omics-{gene}"),
                source_span=f"gene={gene}|effect=up",
                context=EvidenceContext(organism="Homo sapiens", disease="ulcerative colitis",
                                        tissue="colon", assay="bulk"),
                stance=Stance.SUPPORTS, effect={"direction": "up"},
                uncertainty="Synthetic test fixture.", quality_flags=["test_fixture"],
                context_match_score=1.0,
            )
            for gene in genes
        ]
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED,
            context_match_score=1.0,
            outputs={"covered": True, "candidates": [{"gene": gene} for gene in genes]},
            capability=ToolCapability(validation_scope="test fixture"),
            evidence_ids=[item.evidence_id for item in evidence],
            candidate_genes=genes,
        )
        return ToolExecution(result=result, evidence=evidence)


class FakeCandidateLiterature(ScientificTool):
    """Deterministic candidate-bound literature tool: one claim per gene."""

    name = "europe_pmc_rag"
    version = "test"

    def run(self, context: ToolContext) -> ToolExecution:
        run_id = new_id("tool")
        evidence = [
            EvidenceItem(
                tool_run_id=run_id, gene_symbol=gene, claim_class=ClaimClass.FACT,
                statement=f"Fixture literature co-mention for {gene}.",
                source=SourceLocator(uri="https://europepmc.org/test", source_id=f"pmid-{gene}",
                                     chunk_id=f"lit-{gene}"),
                source_span=f"gene={gene}|disease=ulcerative colitis",
                context=EvidenceContext(disease="ulcerative colitis", assay="fixture"),
                stance=Stance.SUPPORTS, uncertainty="Synthetic test fixture.",
                quality_flags=["test_fixture"], context_match_score=1.0,
            )
            for gene in context.candidate_genes
        ]
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED,
            context_match_score=1.0,
            outputs={"search_hits": len(evidence), "extracted_claims": len(evidence),
                     "search_hits_are_evidence": False},
            capability=ToolCapability(validation_scope="test fixture"),
            evidence_ids=[item.evidence_id for item in evidence],
        )
        return ToolExecution(result=result, evidence=evidence)


def _registry() -> ToolRegistry:
    return ToolRegistry([FakeOmicsCandidates(), FakeCandidateLiterature()])


def _runtime(tmp_path) -> LangGraphRuntime:
    return LangGraphRuntime(
        runs_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        planner=Planner(None, _registry()),
        registry=_registry(),
    )


def test_plan_step_requires_candidate_bound_for_evidence_lane():
    with pytest.raises(ValueError, match="evidence_lane requires candidate_bound=True"):
        PlanStep(step_id="literature", name="literature", evidence_lane="literature")


def test_deterministic_planner_marks_candidate_bound_evidence_steps():
    plan = Planner(None).deterministic(_task())
    by_id = {step.step_id: step for step in plan.steps}
    assert by_id["literature"].candidate_bound is True
    assert by_id["literature"].evidence_lane == "literature"
    assert by_id["trials"].candidate_bound is True
    assert by_id["trials"].evidence_lane == "trials"
    assert by_id["genetics"].candidate_bound is True
    assert by_id["genetics"].evidence_lane == "genetics"
    assert by_id["omics_candidates"].candidate_bound is False
    assert by_id["bulk"].candidate_bound is False


def test_planner_rejects_candidate_bound_step_without_candidate_producer():
    plan = ExecutionPlan(
        task_id=_task().task_id,
        planner_backend="test",
        steps=[
            PlanStep(step_id="scope", name="scope", tool="disease_resolver"),
            PlanStep(
                step_id="literature", name="literature", tool="europe_pmc_rag",
                dependencies=["scope"], candidate_bound=True, evidence_lane="literature",
            ),
        ],
    )
    with pytest.raises(ValueError, match="no candidate-producing dependency"):
        Planner(None)._validate(_task(), plan)


def test_fresh_run_stamps_candidate_bound_digest(tmp_path):
    run_dir = tmp_path / "runs" / "run-fresh"
    runtime = _runtime(tmp_path)
    status = runtime.run(_task(), run_id="run-fresh")
    assert status["terminal_status"] == "completed"
    rows = _jsonl(run_dir / "tool_results.jsonl")
    literature = [row for row in rows if row["tool_name"] == "europe_pmc_rag"]
    assert len(literature) == 1
    meta = literature[0]["outputs"][CANDIDATE_BOUND_OUTPUT_KEY]
    assert meta["step_id"] == "literature"
    assert meta["evidence_lane"] == "literature"
    assert meta["candidate_digest"] == candidate_universe_digest(
        ["GENE1", "GENE2", "GENE3"]
    )
    assert literature[0]["supersedes_tool_run_id"] is None


def test_resume_drops_stale_candidate_bound_evidence_and_supersedes(tmp_path):
    task = _task()
    run_dir = tmp_path / "runs" / "run-stale"
    store = EvidenceStore(run_dir)
    store.save_task(task)

    omics = FakeOmicsCandidates().run(ToolContext(task=task, run_dir=run_dir,
                                                  cache_dir=tmp_path / "cache",
                                                  candidate_genes=[], prior_results=[],
                                                  settings=None))
    for item in omics.evidence:
        store.add_evidence(item)
    store.add_tool_result(omics.result)

    stale_run_id = new_id("tool")
    stale_evidence = [
        EvidenceItem(
            tool_run_id=stale_run_id, gene_symbol=gene, claim_class=ClaimClass.FACT,
            statement=f"Stale literature claim for {gene}.",
            source=SourceLocator(uri="https://europepmc.org/test", source_id=f"pmid-{gene}",
                                 chunk_id=f"stale-{gene}"),
            source_span=f"gene={gene}|old-candidate-set",
            context=EvidenceContext(disease="ulcerative colitis", assay="fixture"),
            stance=Stance.SUPPORTS, uncertainty="Synthetic test fixture.",
            quality_flags=["test_fixture"], context_match_score=1.0,
        )
        for gene in ("GENE1", "GENE2")
    ]
    stale_result = ToolResult(
        tool_run_id=stale_run_id, tool_name="europe_pmc_rag", tool_version="test",
        status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED,
        context_match_score=1.0,
        outputs={
            CANDIDATE_BOUND_OUTPUT_KEY: {
                "step_id": "literature",
                "candidate_digest": candidate_universe_digest(["GENE1", "GENE2"]),
                "evidence_lane": "literature",
            },
            "search_hits": 2, "extracted_claims": 2, "search_hits_are_evidence": False,
        },
        capability=ToolCapability(validation_scope="test fixture"),
        evidence_ids=[item.evidence_id for item in stale_evidence],
    )
    for item in stale_evidence:
        store.add_evidence(item)
    store.add_tool_result(stale_result)
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": ["omics_candidates", "literature"],
        "candidate_genes": ["GENE1", "GENE2", "GENE3"],
        "candidate_digest": candidate_universe_digest(["GENE1", "GENE2", "GENE3"]),
        "tool_calls": 2,
        "revision_history": [],
    })

    stale_evidence_ids = {item.evidence_id for item in stale_evidence}
    runtime = _runtime(tmp_path)
    status = runtime.run(task, run_id="run-stale", resume=True)
    assert status["terminal_status"] == "completed"

    rows = _jsonl(run_dir / "tool_results.jsonl")
    literature = [row for row in rows if row["tool_name"] == "europe_pmc_rag"]
    assert len(literature) == 2
    assert literature[0]["tool_run_id"] == stale_run_id
    active = literature[1]
    assert active["supersedes_tool_run_id"] == stale_run_id
    assert active["outputs"][CANDIDATE_BOUND_OUTPUT_KEY]["candidate_digest"] == candidate_universe_digest(
        ["GENE1", "GENE2", "GENE3"]
    )

    trace = _jsonl(run_dir / "trace.jsonl")
    superseded = [row for row in trace if row["event_type"] == "evidence_superseded"]
    assert superseded and superseded[0]["detail"]["supersedes_tool_run_id"] == stale_run_id
    replan = [row for row in trace if row["event_type"] == "replan" and row["state"] == "resume"]
    assert replan and "literature" in replan[0]["detail"]["steps"]

    ranked = json.loads((run_dir / "ranked_targets.json").read_text(encoding="utf-8"))
    ranked_evidence_ids = {
        evidence_id for row in ranked for evidence_id in row["evidence_ids"]
    }
    assert not (ranked_evidence_ids & stale_evidence_ids)


def test_resume_reuses_digest_matched_candidate_bound_result(tmp_path):
    task = _task()
    run_dir = tmp_path / "runs" / "run-reuse"
    store = EvidenceStore(run_dir)
    store.save_task(task)

    omics = FakeOmicsCandidates().run(ToolContext(task=task, run_dir=run_dir,
                                                  cache_dir=tmp_path / "cache",
                                                  candidate_genes=[], prior_results=[],
                                                  settings=None))
    for item in omics.evidence:
        store.add_evidence(item)
    store.add_tool_result(omics.result)

    matched_digest = candidate_universe_digest(["GENE1", "GENE2", "GENE3"])
    lit = FakeCandidateLiterature().run(ToolContext(
        task=task, run_dir=run_dir, cache_dir=tmp_path / "cache",
        candidate_genes=["GENE1", "GENE2", "GENE3"], prior_results=[omics.result],
        settings=None,
    ))
    lit.result.outputs[CANDIDATE_BOUND_OUTPUT_KEY] = {
        "step_id": "literature",
        "candidate_digest": matched_digest,
        "evidence_lane": "literature",
    }
    for item in lit.evidence:
        store.add_evidence(item)
    store.add_tool_result(lit.result)
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": ["omics_candidates", "literature"],
        "candidate_genes": ["GENE1", "GENE2", "GENE3"],
        "candidate_digest": matched_digest,
        "tool_calls": 2,
        "revision_history": [],
    })

    runtime = _runtime(tmp_path)
    status = runtime.run(task, run_id="run-reuse", resume=True)
    assert status["terminal_status"] == "completed"
    rows = _jsonl(run_dir / "tool_results.jsonl")
    literature = [row for row in rows if row["tool_name"] == "europe_pmc_rag"]
    # digest-matched completed steps are skipped without re-execution
    assert len(literature) == 1
    final_checkpoint = json.loads((run_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert final_checkpoint["candidate_digest"] == matched_digest
    trace = _jsonl(run_dir / "trace.jsonl")
    assert not any(row["event_type"] == "evidence_superseded" for row in trace)
    assert not any(
        row["event_type"] == "replan" and row["state"] == "resume" for row in trace
    )
