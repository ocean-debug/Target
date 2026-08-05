from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from target_agent.contracts import (
    ClaimClass, EqtlColocalizationResultInput, EvidenceContext, EvidenceItem,
    FineMappingColumnMap, FineMappingResultInput, GeneticEvidencePayload,
    GwasColumnMap, GwasSummaryStatsInput, LDReferenceSpec, SourceLocator,
    Stance, TaskConstraints, TaskContext, TaskSpec, ToolCapability, ToolResult, ToolStatus,
    CoverageStatus,
)
from target_agent.planner import Planner
from target_agent.ranking import rank_targets
from target_agent.runtime import TargetDiscoveryRuntime
from target_agent.runtime_langgraph import LangGraphRuntime
from target_agent.settings import Settings
from target_agent.tools.base import ScientificTool, ToolContext, ToolExecution, ToolRegistry
from target_agent.tools.genetics import (
    EqtlColocalizationAuditTool, FineMappingAuditTool,
    GeneticsCandidateExtractionTool, GeneticsInputAuditTool,
)
from target_agent.tools.opentargets import OpenTargetsTool


FIXTURES = Path(__file__).parent / "fixtures" / "genetics"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gwas(**updates) -> GwasSummaryStatsInput:
    payload = {
        "asset_id": "gwas-l1", "relative_path": "gwas.tsv", "sha256": _sha(FIXTURES / "gwas.tsv"),
        "file_format": "tsv", "genome_build": "GRCh38", "study_id": "GWAS-1",
        "phenotype": "lung adenocarcinoma", "ancestry": "EUR", "sample_size": 10_000,
        "source_uri": "https://example.org/gwas-1", "source_version": "fixture-1",
        "effect_scale": "beta",
        "columns": GwasColumnMap(
            chromosome="chrom", position="pos", effect_allele="ea", other_allele="oa",
            effect="beta", standard_error="se", p_value="p", effect_allele_frequency="eaf",
            variant_id="variant", locus_id="locus",
        ),
    }
    payload.update(updates)
    return GwasSummaryStatsInput(**payload)


def _fine(**updates) -> FineMappingResultInput:
    payload = {
        "asset_id": "fine-l1", "relative_path": "fine_mapping.tsv",
        "sha256": _sha(FIXTURES / "fine_mapping.tsv"), "file_format": "tsv",
        "genome_build": "GRCh38", "study_id": "GWAS-1", "phenotype": "lung adenocarcinoma",
        "ancestry": "EUR", "sample_size": 10_000, "source_uri": "https://example.org/fine-1",
        "source_version": "fixture-1", "method": "susie", "method_version": "0.12.35",
        "ld_reference": LDReferenceSpec(
            reference_id="1000G-EUR", ancestry="EUR", genome_build="GRCh38",
            source_uri="https://example.org/ld", version="fixture-1", sha256="a" * 64,
            sample_size=503, matched_to_study=True,
        ),
        "columns": FineMappingColumnMap(
            chromosome="chrom", position="pos", effect_allele="ea", other_allele="oa",
            signal_posterior="pip", credible_set_id="credible_set",
            locus_id="locus", variant_id="variant",
        ),
    }
    payload.update(updates)
    return FineMappingResultInput(**payload)


def _coloc(tissue: str = "lung") -> EqtlColocalizationResultInput:
    return EqtlColocalizationResultInput(
        asset_id="coloc-l1", relative_path="coloc.tsv", sha256=_sha(FIXTURES / "coloc.tsv"),
        file_format="tsv", genome_build="GRCh38", study_id="EQTL-1",
        phenotype="lung adenocarcinoma", ancestry="EUR", sample_size=500,
        source_uri="https://example.org/coloc-1", source_version="fixture-1",
        method="coloc_susie", method_version="5.2.3", gwas_study_id="GWAS-1",
        eqtl_study_id="EQTL-1", eqtl_ancestry="EUR", tissue=tissue,
        minimum_variant_overlap_used=10, prior_p1=1e-4, prior_p2=1e-4, prior_p12=1e-5,
        sensitivity_analysis_passed=True, sample_overlap="none",
        columns={
            "gene": "gene", "locus_id": "locus", "signal_id": "signal",
            "chromosome": "chrom", "position": "pos",
            "gwas_effect_allele": "gwas_ea", "gwas_other_allele": "gwas_oa",
            "eqtl_effect_allele": "eqtl_ea", "eqtl_other_allele": "eqtl_oa",
            "eqtl_beta": "eqtl_beta", "pp0": "pp0", "pp1": "pp1", "pp2": "pp2",
            "pp3": "pp3", "pp4": "pp4", "n_variants": "n_variants", "variant_id": "variant",
        },
        harmonized_variants={
            "relative_path": "coloc_harmonized_variants.tsv",
            "sha256": _sha(FIXTURES / "coloc_harmonized_variants.tsv"), "file_format": "tsv",
            "columns": {
                "gene": "gene", "locus_id": "locus", "signal_id": "signal",
                "chromosome": "chrom", "position": "pos",
                "gwas_effect_allele": "gwas_ea", "gwas_other_allele": "gwas_oa",
                "eqtl_effect_allele": "eqtl_ea", "eqtl_other_allele": "eqtl_oa",
                "variant_id": "variant",
            },
        },
        sensitivity_artifact={
            "relative_path": "coloc_sensitivity.json",
            "sha256": _sha(FIXTURES / "coloc_sensitivity.json"), "media_type": "application/json",
        },
    )


def _task(*assets, tissue: str = "lung") -> TaskSpec:
    return TaskSpec(
        task_type="gwas_locus_to_target", question="Map the disease locus to an auditable target",
        context=TaskContext(disease="lung adenocarcinoma", tissue=tissue, genome_build="GRCh38", ancestry="EUR"),
        genetics_inputs=list(assets), constraints=TaskConstraints(
            genetics={"minimum_coloc_variant_overlap": 10},
        ),
    )


def _context(tmp_path: Path, task: TaskSpec, prior=None) -> ToolContext:
    settings = Settings(
        TARGET_AGENT_INPUT_ROOT=FIXTURES,
        TARGET_AGENT_RUN_DIR=tmp_path / "runs",
        TARGET_AGENT_CACHE_DIR=tmp_path / "cache",
    )
    return ToolContext(
        task=task, run_dir=tmp_path / "run", cache_dir=tmp_path / "cache",
        candidate_genes=[], prior_results=list(prior or []), settings=settings,
    )


def _run_chain(tmp_path: Path, task: TaskSpec):
    context = _context(tmp_path, task)
    audit = GeneticsInputAuditTool().run(context)
    context.prior_results.append(audit.result)
    fine = FineMappingAuditTool().run(context)
    context.prior_results.append(fine.result)
    coloc = EqtlColocalizationAuditTool().run(context)
    context.prior_results.append(coloc.result)
    candidates = GeneticsCandidateExtractionTool().run(context)
    return audit, fine, coloc, candidates


def test_precomputed_genetics_chain_produces_only_audited_locus_to_gene_candidate(tmp_path):
    audit, fine, coloc, candidates = _run_chain(tmp_path, _task(_gwas(), _fine(), _coloc()))
    assert audit.result.status.value == "success"
    assert fine.result.outputs["credible_sets"][0]["formal_score_eligible"] is True
    assert coloc.result.outputs["colocalizations"][0]["formal_score_eligible"] is True
    assert candidates.result.candidate_genes == ["IL6"]
    mapped = next(item for item in candidates.evidence if item.gene_symbol == "IL6")
    assert mapped.claim_class == ClaimClass.INFERRED
    assert mapped.genetic_evidence and mapped.genetic_evidence.causal_status == "not_established"
    assert "not a causal conclusion" in mapped.statement


def test_gwas_association_without_locus_to_gene_evidence_remains_unresolved(tmp_path):
    task = _task(_gwas())
    context = _context(tmp_path, task)
    audit = GeneticsInputAuditTool().run(context)
    context.prior_results.append(audit.result)
    extracted = GeneticsCandidateExtractionTool().run(context)
    assert extracted.result.candidate_genes == []
    assert extracted.result.outputs["unresolved_gwas_loci"]
    assert all(item.gene_symbol is None for item in extracted.evidence)
    assert all(item.genetic_evidence and not item.genetic_evidence.formal_score_eligible for item in extracted.evidence)


def test_context_mismatched_eqtl_cannot_enter_formal_candidate_set(tmp_path):
    _, _, coloc, candidates = _run_chain(tmp_path, _task(_gwas(), _fine(), _coloc("brain"), tissue="lung"))
    row = coloc.result.outputs["colocalizations"][0]
    assert row["formal_score_eligible"] is False
    assert "eqtl_context_mismatch" in row["rejection_reasons"]
    assert candidates.result.candidate_genes == []


def test_ld_build_mismatch_invalidates_credible_set(tmp_path):
    bad_ld = LDReferenceSpec(
        reference_id="1000G-EUR", ancestry="EUR", genome_build="GRCh37",
        source_uri="https://example.org/ld", version="fixture-1", sha256="a" * 64,
        sample_size=503, matched_to_study=True,
    )
    task = _task(_gwas(), _fine(ld_reference=bad_ld))
    context = _context(tmp_path, task)
    audit = GeneticsInputAuditTool().run(context)
    context.prior_results.append(audit.result)
    fine = FineMappingAuditTool().run(context)
    row = fine.result.outputs["credible_sets"][0]
    assert row["formal_score_eligible"] is False
    assert "ld_build_or_ancestry_mismatch" in row["rejection_reasons"]


def test_genetics_asset_path_is_controlled():
    with pytest.raises(ValidationError, match="controlled input root"):
        _gwas(relative_path="../secret.tsv")
    with pytest.raises(ValidationError, match="controlled input root"):
        _gwas(relative_path="/tmp/secret.tsv")


def test_genetics_task_rejects_disease_and_study_contract_mismatch():
    with pytest.raises(ValidationError, match="phenotype must match"):
        _task(_gwas(phenotype="Alzheimer disease"))
    with pytest.raises(ValidationError, match="reference a supplied GWAS study"):
        _task(_gwas(), _fine(study_id="GWAS-OTHER"))


def _evidence(
    genetic: GeneticEvidencePayload | None,
    *,
    raw_score: float | None = None,
    context_match_score: float = 1.0,
) -> EvidenceItem:
    effect = {"genetic_score": raw_score} if raw_score is not None else {}
    return EvidenceItem(
        tool_run_id="tool-test", gene_symbol="IL6", claim_class=ClaimClass.INFERRED,
        statement="Statistical evidence supports prioritization but does not establish causality.",
        source=SourceLocator(uri="https://example.org/evidence", source_id="fixture", chunk_id="row-1"),
        source_span="fixture span", context=EvidenceContext(
            disease="lung adenocarcinoma", genome_build="GRCh38", ancestry="EUR",
            study_id="GWAS-1", locus_id="L1", signal_id="CS1",
        ),
        stance=Stance.SUPPORTS, effect=effect, uncertainty="Model-dependent statistical evidence.",
        context_match_score=context_match_score, genetic_evidence=genetic,
    )


def test_ranking_ignores_free_form_and_database_aggregate_genetic_scores():
    raw = rank_targets(["IL6"], [_evidence(None, raw_score=1.0)], [])[0]
    aggregate = rank_targets(["IL6"], [_evidence(GeneticEvidencePayload(
        evidence_type="open_targets_genetic_association", analysis_level="database_aggregate",
        study_id="OpenTargets", gene_symbol="IL6", strength=1.0, formal_score_eligible=False,
    ))], [])[0]
    formal_payload = GeneticEvidencePayload(
        evidence_type="locus_to_gene", analysis_level="colocalization_supported",
        study_id="GWAS-1", molecular_study_id="EQTL-1",
        locus_id="L1", signal_id="CS1", gene_symbol="IL6",
        method="coloc_susie", method_version="5.2.3", strength=0.9, formal_score_eligible=True,
    )
    formal = rank_targets(["IL6"], [_evidence(formal_payload)], [])[0]
    # Simulate a corrupted/deserialized object that bypassed Pydantic so the
    # scorer's independent context gate is exercised as a second boundary.
    low_context_item = _evidence(formal_payload).model_copy(
        update={"context_match_score": 0.49},
    )
    context_mismatch = rank_targets(
        ["IL6"], [low_context_item], [],
    )[0]
    assert raw.scores.human_genetics == 0
    assert aggregate.scores.human_genetics == 0
    assert context_mismatch.scores.human_genetics == 0
    assert formal.scores.human_genetics == 22.5


def test_open_targets_splits_genetic_and_somatic_scores_without_formal_genetic_credit(
    tmp_path, monkeypatch,
):
    payload = {
        "data": {
            "disease": {
                "id": "EFO_TEST",
                "name": "test disease",
                "associatedTargets": {
                    "rows": [{
                        "score": 0.95,
                        "datatypeScores": [
                            {"id": "genetic_association", "score": 0.3},
                            {"id": "somatic_mutation", "score": 0.9},
                        ],
                        "target": {
                            "id": "ENSG-IL6", "approvedSymbol": "IL6",
                            "approvedName": "interleukin 6", "biotype": "protein_coding",
                        },
                    }],
                },
            },
        },
        "resolved_disease_id": "EFO_TEST",
        "selected_genetic_symbols": ["IL6"],
        "target_clinical_candidates": {},
        "clinical_warning": None,
    }
    task = TaskSpec(
        task_type="disease_to_target", question="Prioritize test-disease targets",
        context=TaskContext(disease="test disease"), candidate_genes=["IL6"],
    )
    settings = Settings(
        TARGET_AGENT_RUN_DIR=tmp_path / "runs",
        TARGET_AGENT_CACHE_DIR=tmp_path / "cache",
    )
    context = ToolContext(
        task=task, run_dir=tmp_path / "run", cache_dir=tmp_path / "cache",
        candidate_genes=["IL6"], prior_results=[], settings=settings,
    )
    tool = OpenTargetsTool()
    monkeypatch.setattr(tool, "_retrieve", lambda *args, **kwargs: (payload, False))

    execution = tool.run(context)
    association = execution.result.outputs["associations"][0]
    assert association["genetic_association_score"] == 0.3
    assert association["somatic_mutation_score"] == 0.9
    assert association["genetic_score"] == 0.3

    aggregate = next(item for item in execution.evidence if item.genetic_evidence is not None)
    somatic = next(item for item in execution.evidence if "somatic_mutation_score" in item.effect)
    assert aggregate.genetic_evidence.analysis_level == "database_aggregate"
    assert aggregate.genetic_evidence.formal_score_eligible is False
    assert somatic.genetic_evidence is None
    assert rank_targets(["IL6"], execution.evidence, [execution.result])[0].scores.human_genetics == 0


def test_formal_genetic_payload_cannot_be_attached_to_a_different_gene():
    payload = GeneticEvidencePayload(
        evidence_type="locus_to_gene", analysis_level="colocalization_supported",
        study_id="GWAS-1", molecular_study_id="EQTL-1", locus_id="L1", signal_id="CS1",
        gene_symbol="TP53", method="coloc_susie", method_version="5.2.3",
        strength=0.9, formal_score_eligible=True,
    )
    with pytest.raises(ValidationError, match="must match EvidenceItem"):
        _evidence(payload)


def test_genetic_evidence_type_and_analysis_level_cannot_be_mixed():
    with pytest.raises(ValidationError, match="requires analysis_level=fine_mapped"):
        GeneticEvidencePayload(
            evidence_type="fine_mapping", analysis_level="colocalization_supported",
            study_id="GWAS-1", locus_id="L1", signal_id="CS1", gene_symbol="IL6",
            strength=0.8, formal_score_eligible=False,
        )


class FakeDiseaseResolver(ScientificTool):
    name = "disease_resolver"
    version = "test"

    def run(self, context: ToolContext) -> ToolExecution:
        return ToolExecution(result=ToolResult(
            tool_name=self.name, tool_version=self.version, status=ToolStatus.SUCCESS,
            coverage_status=CoverageStatus.COVERED, context_match_score=1.0,
            outputs={"covered": True, "normalized_disease": context.task.context.disease},
            capability=ToolCapability(validation_scope="test fixture"),
        ), evidence=[])


def test_gwas_workflow_is_planned_and_legacy_langgraph_outputs_match(tmp_path):
    task = _task(_gwas(), _fine(), _coloc())
    registry = ToolRegistry([
        FakeDiseaseResolver(),
        GeneticsInputAuditTool(), FineMappingAuditTool(), EqtlColocalizationAuditTool(),
        GeneticsCandidateExtractionTool(),
    ])
    planner = Planner(None, registry)
    plan = planner.deterministic(task)
    assert [step.tool for step in plan.steps if step.tool] == [
        "disease_resolver", "genetics_input_audit", "fine_mapping_audit", "eqtl_colocalization_audit",
        "genetics_candidate_extraction",
    ]
    settings = Settings(TARGET_AGENT_INPUT_ROOT=FIXTURES, TARGET_AGENT_CACHE_DIR=tmp_path / "cache")
    outputs = []
    for runtime_class, name in ((TargetDiscoveryRuntime, "legacy"), (LangGraphRuntime, "langgraph")):
        runtime = runtime_class(
            runs_dir=tmp_path / name / "runs", cache_dir=tmp_path / "cache",
            registry=registry, planner=planner, settings=settings,
        )
        status = runtime.run(task, run_id="run-genetics")
        ranking_path = tmp_path / name / "runs" / "run-genetics" / "ranked_targets.json"
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        outputs.append((
            status["terminal_status"],
            [(row["gene"], row["scores"], row["decision"]) for row in ranking],
        ))
    assert outputs[0] == outputs[1]
