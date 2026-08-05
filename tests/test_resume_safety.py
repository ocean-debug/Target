from __future__ import annotations

import json

import pytest

from target_agent.contracts import (
    ClaimClass,
    CoverageStatus,
    EvidenceContext,
    EvidenceItem,
    GeneticEvidencePayload,
    GwasColumnMap,
    GwasSummaryStatsInput,
    ReviewerFinding,
    SourceLocator,
    Stance,
    TaskConstraints,
    TaskContext,
    TaskSpec,
    TerminalStatus,
    ToolCapability,
    ToolResult,
    ToolStatus,
    new_id,
)
from target_agent.planner import Planner
from target_agent.runtime import TargetDiscoveryRuntime
from target_agent.runtime_langgraph import LangGraphRuntime
from target_agent.store import EvidenceStore
from target_agent.tools.base import ScientificTool, ToolContext, ToolExecution, ToolRegistry

from .fakes import FakeGenericOmics, FakeLiterature, FakeOpenTargets


RUNTIMES = [TargetDiscoveryRuntime, LangGraphRuntime]


def _runtime(runtime_class, tmp_path):
    return runtime_class(
        runs_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        planner=Planner(None),
        registry=ToolRegistry([FakeGenericOmics(), FakeOpenTargets(), FakeLiterature()]),
    )


def _task(*, candidate_genes: list[str] | None = None) -> TaskSpec:
    return TaskSpec(
        task_id="task-resume-safety",
        task_type="disease_to_target",
        question="Find traceable UC targets",
        context=TaskContext(
            disease="ulcerative colitis",
            disease_id="MONDO_0005101",
            tissue="rectum",
            cell_type="T cell",
            desired_phenotype="restore state",
        ),
        candidate_genes=candidate_genes or [],
    )


def _stored_result(tool_name: str, candidate_genes: list[str] | None = None) -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        tool_version="resume-test",
        status=ToolStatus.SUCCESS,
        coverage_status=CoverageStatus.COVERED,
        context_match_score=1.0,
        candidate_genes=candidate_genes or [],
        capability=ToolCapability(validation_scope="resume safety fixture"),
    )


class _GwasFixtureTool(ScientificTool):
    version = "resume-test"

    def __init__(
        self,
        name: str,
        *,
        mapped_genes: list[str],
        tamper_extraction_evidence: bool = False,
        explode_extraction: bool = False,
    ):
        self.name = name
        self.mapped_genes = mapped_genes
        self.tamper_extraction_evidence = tamper_extraction_evidence
        self.explode_extraction = explode_extraction

    def run(self, context: ToolContext) -> ToolExecution:
        if self.name == "genetics_candidate_extraction" and self.explode_extraction:
            raise RuntimeError("fixture extraction failure")
        run_id = new_id("tool")
        prior = {result.tool_name: result for result in context.prior_results}
        outputs = {"covered": True}
        inputs = {}
        candidate_genes: list[str] = []
        evidence: list[EvidenceItem] = []

        if self.name == "genetics_input_audit":
            outputs["assets"] = [{
                "kind": "gwas_summary_statistics",
                "study_id": "GWAS-1",
                "genome_build": "GRCh38",
                "ancestry": "EUR",
            }]
        elif self.name == "fine_mapping_audit":
            outputs["credible_sets"] = [{
                "study_id": "GWAS-1",
                "locus_id": "L1",
                "credible_set_id": "CS1",
                "formal_score_eligible": True,
            }]
        elif self.name == "eqtl_colocalization_audit":
            inputs = {
                "genetics_input_audit_tool_run_id": prior["genetics_input_audit"].tool_run_id,
                "fine_mapping_tool_run_id": prior["fine_mapping_audit"].tool_run_id,
            }
            outputs["colocalizations"] = [{
                "gene": gene,
                "study_id": "GWAS-1",
                "gwas_study_id": "GWAS-1",
                "locus_id": "L1",
                "signal_id": "CS1",
                "pp4": 0.9,
                "formal_score_eligible": True,
            } for gene in self.mapped_genes]
        elif self.name == "genetics_candidate_extraction":
            inputs = {
                "genetics_input_audit_tool_run_id": prior["genetics_input_audit"].tool_run_id,
                "fine_mapping_tool_run_id": prior["fine_mapping_audit"].tool_run_id,
                "colocalization_tool_run_id": prior["eqtl_colocalization_audit"].tool_run_id,
            }
            candidate_genes = list(self.mapped_genes)
            outputs = {"covered": bool(candidate_genes), "candidate_genes": candidate_genes}
            if not self.tamper_extraction_evidence:
                evidence = [self._formal_evidence(run_id, gene) for gene in candidate_genes]
        elif self.name == "open_targets":
            candidate_genes = ["TP53"]
            outputs.update({"associations": [{"gene": "TP53"}], "candidate_genes": candidate_genes})

        covered = outputs.get("covered") is True
        return ToolExecution(
            result=ToolResult(
                tool_run_id=run_id,
                tool_name=self.name,
                tool_version=self.version,
                status=ToolStatus.SUCCESS if covered else ToolStatus.PARTIAL,
                coverage_status=CoverageStatus.COVERED if covered else CoverageStatus.PARTIAL,
                context_match_score=1.0 if covered else 0.0,
                inputs=inputs,
                outputs=outputs,
                candidate_genes=candidate_genes,
                evidence_ids=[item.evidence_id for item in evidence],
                capability=ToolCapability(validation_scope="GWAS runtime fixture"),
            ),
            evidence=evidence,
        )

    @staticmethod
    def _formal_evidence(tool_run_id: str, gene: str) -> EvidenceItem:
        return EvidenceItem(
            tool_run_id=tool_run_id,
            gene_symbol=gene,
            claim_class=ClaimClass.INFERRED,
            statement="A fixture shared-signal analysis supports a test locus-to-gene hypothesis.",
            source=SourceLocator(
                uri="https://example.org/coloc-fixture",
                source_id="GWAS-1|EQTL-1",
                chunk_id=f"L1-CS1-{gene}",
            ),
            source_span=f"locus=L1|signal=CS1|gene={gene}|PP4=0.9",
            context=EvidenceContext(
                disease="lung adenocarcinoma",
                tissue="lung",
                genome_build="GRCh38",
                ancestry="EUR",
                study_id="GWAS-1",
                locus_id="L1",
                signal_id="CS1",
            ),
            stance=Stance.SUPPORTS,
            effect_direction="unclear",
            uncertainty="Synthetic test evidence; shared signal does not establish causality.",
            context_match_score=1.0,
            genetic_evidence=GeneticEvidencePayload(
                evidence_type="locus_to_gene",
                analysis_level="colocalization_supported",
                study_id="GWAS-1",
                molecular_study_id="EQTL-1",
                locus_id="L1",
                signal_id="CS1",
                gene_symbol=gene,
                method="coloc_susie",
                method_version="fixture",
                strength=0.9,
                formal_score_eligible=True,
            ),
        )


def _gwas_task(*, max_initial_candidates: int = 20) -> TaskSpec:
    return TaskSpec(
        task_id="task-gwas-runtime-safety",
        task_type="gwas_locus_to_target",
        question="Map an audited lung adenocarcinoma locus to candidate targets",
        context=TaskContext(
            disease="lung adenocarcinoma",
            organism="Homo sapiens",
            tissue="lung",
            genome_build="GRCh38",
            ancestry="EUR",
        ),
        constraints=TaskConstraints(max_initial_candidates=max_initial_candidates),
        candidate_genes=["BYPASS"],
        genetics_inputs=[GwasSummaryStatsInput(
            asset_id="gwas-runtime-fixture",
            relative_path="genetics/gwas.tsv",
            sha256="a" * 64,
            file_format="tsv",
            genome_build="GRCh38",
            study_id="GWAS-1",
            phenotype="lung adenocarcinoma",
            ancestry="EUR",
            sample_size=10_000,
            source_uri="https://example.org/gwas-runtime-fixture",
            source_version="fixture-1",
            effect_scale="beta",
            columns=GwasColumnMap(
                chromosome="chromosome",
                position="position",
                effect_allele="effect_allele",
                other_allele="other_allele",
                effect="beta",
                standard_error="standard_error",
                p_value="p_value",
            ),
        )],
    )


def _gwas_runtime(
    runtime_class,
    tmp_path,
    *,
    mapped_genes: list[str],
    tamper_extraction_evidence: bool = False,
    explode_extraction: bool = False,
):
    names = [
        "disease_resolver",
        "genetics_input_audit",
        "fine_mapping_audit",
        "eqtl_colocalization_audit",
        "genetics_candidate_extraction",
        "open_targets",
    ]
    registry = ToolRegistry([
        _GwasFixtureTool(
            name,
            mapped_genes=mapped_genes,
            tamper_extraction_evidence=tamper_extraction_evidence,
            explode_extraction=explode_extraction,
        ) for name in names
    ])
    return runtime_class(
        runs_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        planner=Planner(None, registry),
        registry=registry,
    )


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_tool_call_budget_is_an_unresolved_major_gap(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    task.constraints.max_tool_calls = 1

    status = runtime.run(task, run_id="run-budget")
    findings = EvidenceStore(runtime.runs_dir / "run-budget").findings()

    assert status["terminal_status"] == "completed_with_gaps"
    assert any(
        finding.category == "coverage_gap"
        and finding.severity == "major"
        and not finding.resolved
        and "budget exhausted" in finding.message
        for finding in findings
    )


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resolved_major_finding_does_not_degrade_terminal_status(runtime_class):
    finding = ReviewerFinding(
        severity="major",
        category="coverage_gap",
        message="A previously missing evidence dimension was repaired.",
        required_action="No action remains.",
        resolved=True,
    )

    status = runtime_class._terminal_status(_task(), [finding], [], [])

    assert status == TerminalStatus.COMPLETED


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_gwas_without_formal_extraction_has_no_ranking(runtime_class, tmp_path):
    runtime = _gwas_runtime(runtime_class, tmp_path, mapped_genes=[])

    status = runtime.run(_gwas_task(), run_id="run-gwas-unresolved")
    run_dir = runtime.runs_dir / "run-gwas-unresolved"

    assert status["terminal_status"] == "needs_input"
    assert not (run_dir / "ranked_targets.json").exists()
    assert EvidenceStore(run_dir).load_checkpoint()["candidate_genes"] == []


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_gwas_ranks_only_formally_mapped_candidates(runtime_class, tmp_path):
    runtime = _gwas_runtime(runtime_class, tmp_path, mapped_genes=["IL6"])

    runtime.run(_gwas_task(), run_id="run-gwas-mapped")
    run_dir = runtime.runs_dir / "run-gwas-mapped"
    ranking = json.loads((run_dir / "ranked_targets.json").read_text())

    assert [row["gene"] for row in ranking] == ["IL6"]
    assert EvidenceStore(run_dir).load_checkpoint()["candidate_genes"] == ["IL6"]


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_gwas_tampered_extraction_without_evidence_has_no_ranking(runtime_class, tmp_path):
    runtime = _gwas_runtime(
        runtime_class,
        tmp_path,
        mapped_genes=["IL6"],
        tamper_extraction_evidence=True,
    )

    status = runtime.run(_gwas_task(), run_id="run-gwas-tampered")
    run_dir = runtime.runs_dir / "run-gwas-tampered"

    assert status["terminal_status"] == "needs_input"
    assert not (run_dir / "ranked_targets.json").exists()


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_gwas_candidate_budget_uses_deterministic_formal_prescreen(runtime_class, tmp_path):
    runtime = _gwas_runtime(runtime_class, tmp_path, mapped_genes=["TP53", "IL6"])

    runtime.run(
        _gwas_task(max_initial_candidates=1),
        run_id="run-gwas-candidate-budget",
    )
    ranking = json.loads(
        (runtime.runs_dir / "run-gwas-candidate-budget" / "ranked_targets.json").read_text()
    )

    assert [row["gene"] for row in ranking] == ["IL6"]


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_failed_genetics_extraction_is_not_misreported_as_needs_input(runtime_class, tmp_path):
    runtime = _gwas_runtime(
        runtime_class,
        tmp_path,
        mapped_genes=["IL6"],
        explode_extraction=True,
    )

    status = runtime.run(_gwas_task(), run_id="run-gwas-failed-extraction")
    run_dir = runtime.runs_dir / "run-gwas-failed-extraction"

    assert status["terminal_status"] == "completed_with_gaps"
    assert not (run_dir / "ranked_targets.json").exists()


def _prepare(runtime, task: TaskSpec, run_id: str):
    store = EvidenceStore(runtime.runs_dir / run_id)
    store.save_task(task)
    plan = runtime.planner.deterministic(task)
    store.save_plan(plan)
    return store, plan


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_revalidates_persisted_plan(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    store, plan = _prepare(runtime, task, "run-tampered-plan")
    plan.steps[0].tool = "not_registered"
    store.save_plan(plan)
    store.checkpoint({"stage": "intake", "completed_steps": [], "tool_calls": 0})

    with pytest.raises(ValueError, match="non-whitelisted tool"):
        runtime.run(task, run_id="run-tampered-plan", resume=True)


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rejects_completed_step_without_dependency_closure(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    store, _ = _prepare(runtime, task, "run-broken-dependencies")
    store.add_tool_result(_stored_result("europe_pmc_rag"))
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": ["literature"],
        "candidate_genes": [],
        "tool_calls": 1,
    })

    with pytest.raises(ValueError, match="missing completed dependencies"):
        runtime.run(task, run_id="run-broken-dependencies", resume=True)


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rejects_completed_tool_step_without_result(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    store, _ = _prepare(runtime, task, "run-missing-result")
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": ["bulk"],
        "candidate_genes": [],
        "tool_calls": 0,
    })

    with pytest.raises(ValueError, match="without matching ToolResult"):
        runtime.run(task, run_id="run-missing-result", resume=True)


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rejects_tool_result_without_completed_step(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    store, _ = _prepare(runtime, task, "run-orphan-result")
    store.add_tool_result(_stored_result("bulk_expression_analysis"))
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": [],
        "candidate_genes": [],
        "tool_calls": 1,
    })

    with pytest.raises(ValueError, match="no completed plan step"):
        runtime.run(task, run_id="run-orphan-result", resume=True)


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rejects_duplicate_tool_run_ids(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    store, _ = _prepare(runtime, task, "run-duplicate-tool-id")
    result = _stored_result("bulk_expression_analysis")
    store.add_tool_result(result)
    store.add_tool_result(result)
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": ["bulk"],
        "candidate_genes": [],
        "tool_calls": 2,
    })

    with pytest.raises(ValueError, match="duplicate ToolResult.tool_run_id"):
        store.assert_referential_integrity()
    with pytest.raises(ValueError, match="duplicate tool_run_id"):
        runtime.run(task, run_id="run-duplicate-tool-id", resume=True)


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rejects_duplicate_evidence_ids(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    store, _ = _prepare(runtime, task, "run-duplicate-evidence-id")
    evidence = EvidenceItem(
        tool_run_id="tool-duplicate-evidence",
        gene_symbol="IL6",
        claim_class=ClaimClass.FACT,
        statement="Synthetic provenance fixture.",
        source=SourceLocator(
            uri="https://example.org/duplicate-evidence",
            source_id="duplicate-evidence",
            chunk_id="row-1",
        ),
        source_span="synthetic fixture span",
        context=EvidenceContext(disease="ulcerative colitis"),
        stance=Stance.SUPPORTS,
        uncertainty="Synthetic test fixture.",
    )
    result = _stored_result("bulk_expression_analysis").model_copy(update={
        "tool_run_id": evidence.tool_run_id,
        "evidence_ids": [evidence.evidence_id],
    })
    store.add_tool_result(result)
    store.add_evidence(evidence)
    store.add_evidence(evidence)
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": ["bulk"],
        "candidate_genes": [],
        "tool_calls": 1,
    })

    with pytest.raises(ValueError, match="duplicate EvidenceItem.evidence_id"):
        store.assert_referential_integrity()
    with pytest.raises(ValueError, match="duplicate evidence_id"):
        runtime.run(task, run_id="run-duplicate-evidence-id", resume=True)


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rebuilds_candidates_from_task_and_tool_results(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task(candidate_genes=["BASE"])
    store, _ = _prepare(runtime, task, "run-candidate-rebuild")
    store.add_tool_result(_stored_result("bulk_expression_analysis", ["RECOVERED"]))
    store.checkpoint({
        "stage": "tool_execution",
        "completed_steps": ["bulk"],
        "candidate_genes": ["INJECTED"],
        "tool_calls": 1,
    })

    runtime.run(task, run_id="run-candidate-rebuild", resume=True)

    final_checkpoint = store.load_checkpoint()
    assert final_checkpoint is not None
    assert "BASE" in final_checkpoint["candidate_genes"]
    assert "RECOVERED" in final_checkpoint["candidate_genes"]
    assert "INJECTED" not in final_checkpoint["candidate_genes"]


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rejects_durable_artifacts_without_task_spec(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    run_dir = runtime.runs_dir / "run-missing-task"
    store = EvidenceStore(run_dir)
    store.checkpoint({
        "stage": "intake",
        "completed_steps": [],
        "candidate_genes": [],
        "tool_calls": 0,
    })

    with pytest.raises(ValueError, match="without task_spec.json"):
        runtime.run(_task(), run_id="run-missing-task", resume=True)

    assert not (run_dir / "task_spec.json").exists()


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_resume_rejects_durable_artifacts_without_checkpoint(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    task = _task()
    run_dir = runtime.runs_dir / "run-missing-checkpoint"
    store = EvidenceStore(run_dir)
    store.save_task(task)
    store.save_plan(runtime.planner.deterministic(task))

    with pytest.raises(ValueError, match="without checkpoint.json"):
        runtime.run(task, run_id="run-missing-checkpoint", resume=True)

    assert not (run_dir / "checkpoint.json").exists()


def _write_legacy_task(run_dir):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "task_spec.json").write_text(json.dumps({
        "contract_version": "2.1.0",
        "task_id": "task-resume-safety",
        "task_type": "disease_to_target",
        "question": "Find traceable UC targets",
        "context": {
            "contract_version": "2.1.0",
            "disease": "ulcerative colitis",
        },
        "constraints": {"contract_version": "2.1.0"},
    }), encoding="utf-8")


def _legacy_input_task() -> TaskSpec:
    return TaskSpec(
        task_id="task-resume-safety",
        task_type="disease_to_target",
        question="Find traceable UC targets",
        context=TaskContext(disease="ulcerative colitis"),
    )


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_nonterminal_legacy_run_cannot_resume_in_place(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    run_dir = runtime.runs_dir / "run-legacy"
    _write_legacy_task(run_dir)
    EvidenceStore(run_dir).checkpoint({
        "stage": "intake",
        "completed_steps": [],
        "candidate_genes": [],
        "tool_calls": 0,
    })

    with pytest.raises(ValueError, match="legacy non-terminal runs cannot resume in place"):
        runtime.run(_legacy_input_task(), run_id="run-legacy", resume=True)

    assert json.loads((run_dir / "task_spec.json").read_text())["contract_version"] == "2.1.0"


@pytest.mark.parametrize("runtime_class", RUNTIMES)
def test_terminal_legacy_run_remains_read_only_and_idempotent(runtime_class, tmp_path):
    runtime = _runtime(runtime_class, tmp_path)
    run_dir = runtime.runs_dir / "run-legacy-terminal"
    _write_legacy_task(run_dir)
    store = EvidenceStore(run_dir)
    store.checkpoint({
        "stage": "terminal",
        "completed_steps": [],
        "candidate_genes": [],
        "tool_calls": 0,
        "terminal_status": "completed_with_gaps",
    })
    store.save_json("status.json", {
        "contract_version": "2.1.0",
        "run_id": "run-legacy-terminal",
        "task_id": "task-resume-safety",
        "state": "terminal",
        "terminal_status": "completed_with_gaps",
        "detail": {},
    })

    status = runtime.run(_legacy_input_task(), run_id="run-legacy-terminal", resume=True)

    assert status["contract_version"] == "2.1.0"
    assert json.loads((run_dir / "task_spec.json").read_text())["contract_version"] == "2.1.0"


@pytest.mark.parametrize("runtime_class", RUNTIMES)
@pytest.mark.parametrize("failure", ["missing", "mismatch"])
def test_terminal_resume_requires_matching_status_witness(runtime_class, tmp_path, failure):
    runtime = _runtime(runtime_class, tmp_path)
    run_dir = runtime.runs_dir / f"run-terminal-{failure}"
    _write_legacy_task(run_dir)
    store = EvidenceStore(run_dir)
    store.checkpoint({
        "stage": "terminal", "completed_steps": [], "candidate_genes": [],
        "tool_calls": 0, "terminal_status": "completed_with_gaps",
    })
    if failure == "mismatch":
        store.save_json("status.json", {
            "contract_version": "2.1.0", "run_id": f"run-terminal-{failure}",
            "task_id": "task-resume-safety", "state": "terminal",
            "terminal_status": "completed", "detail": {},
        })

    with pytest.raises(ValueError, match="terminal checkpoint"):
        runtime.run(
            _legacy_input_task(), run_id=f"run-terminal-{failure}", resume=True,
        )
