from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from target_agent.contracts import (
    ClaimClass,
    CoverageStatus,
    EqtlColocalizationResultInput,
    EvidenceContext,
    EvidenceItem,
    GeneticEvidencePayload,
    GwasColumnMap,
    GwasSummaryStatsInput,
    SourceLocator,
    Stance,
    TaskConstraints,
    TaskContext,
    TaskSpec,
    ToolDescriptor,
    ToolStatus,
)
from target_agent.settings import Settings
from target_agent.tools.base import (
    ScientificTool,
    ToolContext,
    execute_tool_safely,
)
from target_agent.tools.genetics import (
    EqtlColocalizationAuditTool,
    GeneticsInputAuditTool,
)


FIXTURES = Path(__file__).parent / "fixtures" / "genetics"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gwas(input_root: Path) -> GwasSummaryStatsInput:
    return GwasSummaryStatsInput(
        asset_id="gwas-edge",
        relative_path="gwas.tsv",
        sha256=_sha(input_root / "gwas.tsv"),
        file_format="tsv",
        genome_build="GRCh38",
        study_id="GWAS-EDGE",
        phenotype="lung adenocarcinoma",
        ancestry="EUR",
        sample_size=10_000,
        source_uri="https://example.org/gwas-edge",
        source_version="fixture-1",
        effect_scale="beta",
        columns=GwasColumnMap(
            chromosome="chrom",
            position="pos",
            effect_allele="ea",
            other_allele="oa",
            effect="beta",
            standard_error="se",
            p_value="p",
            effect_allele_frequency="eaf",
            variant_id="variant",
            locus_id="locus",
        ),
    )


def _coloc(
    input_root: Path,
    *,
    table: str = "coloc.tsv",
    manifest: str = "coloc_harmonized_variants.tsv",
) -> EqtlColocalizationResultInput:
    return EqtlColocalizationResultInput(
        asset_id="coloc-edge",
        relative_path=table,
        sha256=_sha(input_root / table),
        file_format="tsv",
        genome_build="GRCh38",
        study_id="EQTL-EDGE",
        phenotype="lung adenocarcinoma",
        ancestry="EUR",
        sample_size=500,
        source_uri="https://example.org/coloc-edge",
        source_version="fixture-1",
        method="coloc_susie",
        method_version="5.2.3",
        gwas_study_id="GWAS-EDGE",
        eqtl_study_id="EQTL-EDGE",
        eqtl_ancestry="EUR",
        tissue="lung",
        minimum_variant_overlap_used=1,
        prior_p1=1e-4,
        prior_p2=1e-4,
        prior_p12=1e-5,
        sensitivity_analysis_passed=True,
        sample_overlap="none",
        columns={
            "gene": "gene",
            "locus_id": "locus",
            "signal_id": "signal",
            "chromosome": "chrom",
            "position": "pos",
            "gwas_effect_allele": "gwas_ea",
            "gwas_other_allele": "gwas_oa",
            "eqtl_effect_allele": "eqtl_ea",
            "eqtl_other_allele": "eqtl_oa",
            "eqtl_beta": "eqtl_beta",
            "pp0": "pp0",
            "pp1": "pp1",
            "pp2": "pp2",
            "pp3": "pp3",
            "pp4": "pp4",
            "n_variants": "n_variants",
            "variant_id": "variant",
        },
        harmonized_variants={
            "relative_path": manifest,
            "sha256": _sha(input_root / manifest),
            "file_format": "tsv",
            "columns": {
                "gene": "gene",
                "locus_id": "locus",
                "signal_id": "signal",
                "chromosome": "chrom",
                "position": "pos",
                "gwas_effect_allele": "gwas_ea",
                "gwas_other_allele": "gwas_oa",
                "eqtl_effect_allele": "eqtl_ea",
                "eqtl_other_allele": "eqtl_oa",
                "variant_id": "variant",
            },
        },
        sensitivity_artifact={
            "relative_path": "coloc_sensitivity.json",
            "sha256": _sha(input_root / "coloc_sensitivity.json"),
            "media_type": "application/json",
        },
    )


def _task(*assets: object) -> TaskSpec:
    return TaskSpec(
        task_type="gwas_locus_to_target",
        question="Map the locus without crossing an evidence boundary",
        context=TaskContext(
            disease="lung adenocarcinoma",
            tissue="lung",
            genome_build="GRCh38",
            ancestry="EUR",
        ),
        genetics_inputs=list(assets),
        constraints=TaskConstraints(
            genetics={"minimum_coloc_variant_overlap": 10},
        ),
    )


def _context(
    tmp_path: Path,
    input_root: Path,
    task: TaskSpec,
    *,
    prior_results: list | None = None,
    step_api_key: str | None = None,
) -> ToolContext:
    settings_kwargs = {
        "TARGET_AGENT_INPUT_ROOT": input_root,
        "TARGET_AGENT_RUN_DIR": tmp_path / "runs",
        "TARGET_AGENT_CACHE_DIR": tmp_path / "cache",
    }
    if step_api_key is not None:
        settings_kwargs["STEP_API_KEY"] = step_api_key
    return ToolContext(
        task=task,
        run_dir=tmp_path / "run",
        cache_dir=tmp_path / "cache",
        candidate_genes=[],
        prior_results=list(prior_results or []),
        settings=Settings(**settings_kwargs),
    )


def _copy_default_inputs(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in (
        "gwas.tsv",
        "coloc.tsv",
        "coloc_harmonized_variants.tsv",
        "coloc_sensitivity.json",
    ):
        shutil.copy2(FIXTURES / name, destination / name)


def test_manifest_input_tampering_is_rejected_by_checksum(tmp_path: Path):
    input_root = tmp_path / "input"
    _copy_default_inputs(input_root)
    task = _task(_gwas(input_root), _coloc(input_root))

    manifest = input_root / "coloc_harmonized_variants.tsv"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "# mutation after contract creation\n",
        encoding="utf-8",
    )

    execution = GeneticsInputAuditTool().run(_context(tmp_path, input_root, task))

    assert execution.result.status == ToolStatus.PARTIAL
    assert execution.result.coverage_status == CoverageStatus.PARTIAL
    failed = next(
        item for item in execution.result.outputs["failed_assets"]
        if item["asset_id"] == "coloc-edge"
    )
    assert failed["error"] == "harmonized_variant_manifest_checksum_mismatch"
    assert all(
        item["asset_id"] != "coloc-edge"
        for item in execution.result.outputs["assets"]
    )


def test_normalized_manifest_tampering_becomes_a_failed_tool_result(tmp_path: Path):
    input_root = tmp_path / "input"
    _copy_default_inputs(input_root)
    task = _task(_gwas(input_root), _coloc(input_root))
    context = _context(tmp_path, input_root, task)
    audit = GeneticsInputAuditTool().run(context)
    assert audit.result.status == ToolStatus.SUCCESS

    coloc_asset = next(
        item for item in audit.result.outputs["assets"]
        if item["asset_id"] == "coloc-edge"
    )
    normalized_manifest = context.run_dir / coloc_asset["harmonized_variant_artifact"]
    normalized_manifest.write_text(
        normalized_manifest.read_text(encoding="utf-8") + "{}\n",
        encoding="utf-8",
    )
    context.prior_results.append(audit.result)

    execution = execute_tool_safely(EqtlColocalizationAuditTool(), context)

    assert execution.result.status == ToolStatus.FAILED
    assert execution.result.coverage_status == CoverageStatus.UNKNOWN
    assert "normalized_artifact_checksum_mismatch" in (execution.result.error or "")
    assert execution.evidence == []


def test_same_locus_multiple_gene_signal_rows_are_not_duplicate_variants(tmp_path: Path):
    task = _task(
        _gwas(FIXTURES),
        _coloc(
            FIXTURES,
            table="coloc_multi.tsv",
            manifest="coloc_multi_harmonized_variants.tsv",
        ),
    )

    execution = GeneticsInputAuditTool().run(_context(tmp_path, FIXTURES, task))

    assert execution.result.status == ToolStatus.SUCCESS
    coloc_asset = next(
        item for item in execution.result.outputs["assets"]
        if item["asset_id"] == "coloc-edge"
    )
    assert coloc_asset["qc"]["rows_valid"] == 2
    assert coloc_asset["qc"]["rows_rejected"] == 0
    assert coloc_asset["harmonized_variant_qc"]["rows_valid"] == 2
    assert "duplicate_variant" not in coloc_asset["qc"]["rejection_reasons"]


@pytest.mark.parametrize(
    ("item_gene", "context_update", "message"),
    [
        ("TP63", {}, "gene must match"),
        ("IL6", {"study_id": "GWAS-OTHER"}, "study/locus/signal"),
        ("IL6", {"locus_id": "L2"}, "study/locus/signal"),
        ("IL6", {"signal_id": "CS2"}, "study/locus/signal"),
    ],
)
def test_formal_evidence_payload_must_match_item_context(
    item_gene: str,
    context_update: dict[str, str],
    message: str,
):
    payload = GeneticEvidencePayload(
        evidence_type="locus_to_gene",
        analysis_level="colocalization_supported",
        study_id="GWAS-EDGE",
        molecular_study_id="EQTL-EDGE",
        locus_id="L1",
        signal_id="CS1",
        gene_symbol="IL6",
        method="coloc_susie",
        method_version="5.2.3",
        strength=0.9,
        formal_score_eligible=True,
    )
    context_payload = {
        "disease": "lung adenocarcinoma",
        "genome_build": "GRCh38",
        "ancestry": "EUR",
        "study_id": "GWAS-EDGE",
        "locus_id": "L1",
        "signal_id": "CS1",
    }
    context_payload.update(context_update)

    with pytest.raises(ValidationError, match=message):
        EvidenceItem(
            tool_run_id="tool-edge",
            gene_symbol=item_gene,
            claim_class=ClaimClass.INFERRED,
            statement="A shared statistical signal supports prioritization without proving causality.",
            source=SourceLocator(
                uri="https://example.org/edge",
                source_id="edge-fixture",
                chunk_id="edge-row-1",
            ),
            source_span="fixture span",
            context=EvidenceContext(**context_payload),
            stance=Stance.SUPPORTS,
            uncertainty="Model- and prior-dependent statistical evidence.",
            context_match_score=1.0,
            genetic_evidence=payload,
        )


class ExplodingTool(ScientificTool):
    name = "exploding_genetics_fixture"
    version = "test"
    descriptor = ToolDescriptor(
        tool_id=name,
        evidence_dimension="genetics",
        description="Raises an unexpected exception for the safe-execution boundary test.",
        execution_policy="fixed_script",
    )

    def run(self, context: ToolContext):
        secret = context.settings.step_api_key.get_secret_value()
        raise RuntimeError(
            f"unexpected failure at {context.run_dir} using {context.settings.input_root}; key={secret}"
        )


def test_unexpected_tool_exception_is_structured_and_redacted(tmp_path: Path):
    input_root = tmp_path / "input"
    input_root.mkdir()
    shutil.copy2(FIXTURES / "gwas.tsv", input_root / "gwas.tsv")
    task = _task(_gwas(input_root))
    context = _context(
        tmp_path,
        input_root,
        task,
        step_api_key="edge-case-secret",
    )

    execution = execute_tool_safely(ExplodingTool(), context)

    assert execution.result.status == ToolStatus.FAILED
    assert execution.result.coverage_status == CoverageStatus.UNKNOWN
    assert execution.result.context_match_score == 0.0
    assert execution.result.outputs == {}
    assert execution.evidence == []
    error = execution.result.error or ""
    assert error.startswith("RuntimeError:")
    assert "[configured-path]" in error
    assert "[redacted]" in error
    assert "edge-case-secret" not in error
    assert str(context.run_dir) not in error
    assert str(context.settings.input_root) not in error
