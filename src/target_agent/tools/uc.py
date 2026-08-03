"""Cached UC omics and measured perturbation Oracles with explicit scope."""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..contracts import (
    ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, SourceLocator,
    Stance, ToolCapability, ToolResult, ToolStatus, new_id,
)
from .base import ScientificTool, ToolContext, ToolExecution


ROOT = Path(__file__).resolve().parents[3]
UC_NAMES = {"ulcerative colitis", "uc", "溃疡性结肠炎"}


def _is_uc(disease: str | None) -> bool:
    return bool(disease and disease.strip().lower() in UC_NAMES)


def _context_match(task_tissue: str | None, task_cell: str | None, tissue: str, cell: str) -> float:
    score = 1.0
    if task_tissue and task_tissue.lower() not in tissue.lower() and tissue.lower() not in task_tissue.lower():
        score -= 0.25
    if task_cell and task_cell.lower() not in cell.lower() and cell.lower() not in task_cell.lower():
        score -= 0.25
    return max(0.0, score)


class UCOmicsSnapshotTool(ScientificTool):
    name = "uc_omics_snapshot"
    version = "2.0.0"

    def run(self, context: ToolContext) -> ToolExecution:
        started = time.perf_counter()
        run_id = new_id("tool")
        disease = context.task.context.disease
        capability = ToolCapability(
            supported_organisms=["Homo sapiens"], supported_tissues=["rectum", "PBMC"],
            supported_cell_types=["T cell", "B cell", "NK cell"],
            training_scope="not applicable", validation_scope="GSE125527 UC case-control donor-pseudobulk snapshot",
        )
        if not _is_uc(disease):
            result = ToolResult(
                tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
                status=ToolStatus.OUT_OF_SCOPE, coverage_status=CoverageStatus.NOT_COVERED,
                context_match_score=0.0, inputs={"disease": disease}, outputs={"covered": False, "candidates": []},
                capability=capability, data_version="GSE125527:v2-snapshot", code_version="2.0.0",
                warnings=["disease_out_of_coverage"],
                limitations=["This cached omics Oracle covers ulcerative colitis only."],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )
            return ToolExecution(result=result, evidence=[])

        payload = json.loads((ROOT / "data" / "derived" / "uc_candidates_v2.json").read_text(encoding="utf-8"))
        rows = payload["candidates"][: context.task.constraints.max_initial_candidates]
        evidence = []
        for row in rows:
            score = _context_match(context.task.context.tissue, context.task.context.cell_type, row["tissue"], row["cell_type"])
            span = (
                f"{row['gene']}|log2FC={row['log2fc']}|FDR={row['fdr']}|"
                f"tissue={row['tissue']}|cell_type={row['cell_type']}"
            )
            evidence.append(EvidenceItem(
                tool_run_id=run_id, gene_symbol=row["gene"], claim_class=ClaimClass.OBSERVED,
                statement=(f"{row['gene']} was differentially expressed in the UC snapshot "
                           f"({row['tissue']}, {row['cell_type']}; log2FC={row['log2fc']:.3g}, FDR={row['fdr']:.3g})."),
                source=SourceLocator(
                    uri=payload["source_uri"], source_id="GSE125527",
                    version=payload["snapshot_date"], section="edgeR donor-pseudobulk", chunk_id=f"uc-omics-{row['gene']}",
                ),
                source_span=span,
                context=EvidenceContext(
                    organism="Homo sapiens", tissue=row["tissue"], cell_type=row["cell_type"],
                    disease="ulcerative colitis", assay=payload["analysis"],
                ),
                stance=Stance.SUPPORTS, effect_direction="increase" if row["log2fc"] > 0 else "decrease",
                effect={"log2fc": row["log2fc"], "fdr": row["fdr"], "legacy_disease_strength_0_60": row["disease_strength_0_60"]},
                uncertainty="Differential expression is associative and cohort-specific.",
                quality_flags=["observational_not_causal", "unadjusted_for_additional_covariates"],
                context_match_score=score,
            ))
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED,
            context_match_score=min(item.context_match_score for item in evidence),
            inputs={"disease": disease, "tissue": context.task.context.tissue, "cell_type": context.task.context.cell_type},
            outputs={"covered": True, "candidates": rows}, capability=capability,
            data_version="GSE125527:v2-snapshot", code_version="2.0.0",
            parameters={"method": payload["analysis"], "max_candidates": len(rows)},
            evidence_ids=[item.evidence_id for item in evidence], limitations=payload["limitations"], cached=True,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return ToolExecution(result=result, evidence=evidence)


class ObservedTCellPerturbationTool(ScientificTool):
    name = "observed_tcell_perturbation"
    version = "2.0.0"

    def run(self, context: ToolContext) -> ToolExecution:
        started = time.perf_counter()
        run_id = new_id("tool")
        capability = ToolCapability(
            supported_organisms=["Homo sapiens"], supported_tissues=["ex vivo blood-derived T cells"],
            supported_cell_types=["primary human T cell"], supported_perturbations=["CRISPRa"],
            training_scope="not applicable", validation_scope="71 measured targets in GSE190604",
        )
        if not _is_uc(context.task.context.disease):
            return ToolExecution(result=ToolResult(
                tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
                status=ToolStatus.OUT_OF_SCOPE, coverage_status=CoverageStatus.NOT_COVERED,
                context_match_score=0.0, inputs={"disease": context.task.context.disease},
                outputs={"covered": False}, capability=capability, data_version="GSE190604:v2-snapshot",
                warnings=["disease_alignment_not_available"],
                limitations=["Disease-signature alignment is implemented only for UC."],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            ), evidence=[])
        payload = json.loads((ROOT / "data" / "derived" / "uc_observed_perturbation_v2.json").read_text(encoding="utf-8"))
        rows = [row for row in payload["targets"] if row["gene"] in context.candidate_genes]
        evidence = []
        for row in rows:
            span = (
                f"{row['gene']}|activation_log2FC={row['activation_log2fc']}|FDR={row['fdr']}|"
                f"n_cells={row['n_cells']}|disease_alignment={row['disease_alignment']}"
            )
            evidence.append(EvidenceItem(
                tool_run_id=run_id, gene_symbol=row["gene"], claim_class=ClaimClass.OBSERVED,
                statement=(f"CRISPRa activated {row['gene']} in primary T cells (target log2FC={row['activation_log2fc']:.3g}); "
                           f"its transcriptomic footprint had UC-signature correlation {row['disease_alignment']:+.3g}."),
                source=SourceLocator(
                    uri=payload["source_uris"][0], source_id="GSE190604+GSE125527",
                    version="v2-snapshot", section="observed perturbation alignment", chunk_id=f"uc-perturb-{row['gene']}",
                ),
                source_span=span,
                context=EvidenceContext(
                    organism="Homo sapiens", tissue="blood-derived", cell_type="primary human T cell",
                    disease="ulcerative colitis signature comparison", assay=payload["assay"], perturbation_type="CRISPRa",
                ),
                stance=Stance.SUPPORTS if row["disease_alignment"] > 0 else Stance.MIXED,
                effect_direction="increase", effect=row,
                uncertainty="The disease-alignment statistic is an observational correlation over only 71 measured targets.",
                quality_flags=["activation_not_inhibition", "limited_target_panel_n71", "observational_mechanism_support"],
                context_match_score=0.8,
            ))
        coverage = CoverageStatus.COVERED if len(rows) == len(context.candidate_genes) else CoverageStatus.PARTIAL
        status = ToolStatus.SUCCESS if coverage == CoverageStatus.COVERED else ToolStatus.PARTIAL
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version, status=status,
            coverage_status=coverage, context_match_score=0.8, inputs={"genes": context.candidate_genes},
            outputs={"covered": bool(rows), "n_screen_targets": payload["n_screen_targets"], "targets": rows,
                     "uncovered_genes": sorted(set(context.candidate_genes) - {r["gene"] for r in rows})},
            capability=capability, data_version="GSE190604+GSE125527:v2-snapshot", code_version="2.0.0",
            parameters={"assay": payload["assay"]}, evidence_ids=[item.evidence_id for item in evidence],
            warnings=["partial_gene_coverage"] if coverage == CoverageStatus.PARTIAL else [],
            limitations=payload["limitations"], cached=True,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return ToolExecution(result=result, evidence=evidence)


class DeltaFactorTool(ScientificTool):
    name = "deltafactor"
    version = "2.0.0"

    def run(self, context: ToolContext) -> ToolExecution:
        run_id = new_id("tool")
        is_uc = _is_uc(context.task.context.disease)
        score = 0.15 if is_uc else 0.0
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.PARTIAL if is_uc else ToolStatus.OUT_OF_SCOPE,
            coverage_status=CoverageStatus.PARTIAL if is_uc else CoverageStatus.NOT_COVERED,
            context_match_score=score,
            inputs={"genes": context.candidate_genes, "requested_context": context.task.context.model_dump(mode="json")},
            outputs={"covered": False, "exploratory_only": True, "formal_score_eligible": False},
            capability=ToolCapability(
                supported_organisms=["Homo sapiens"], supported_tissues=["K562 cell line"],
                supported_cell_types=["K562"], supported_perturbations=["CRISPR perturbation prediction"],
                training_scope="Norman K562 perturbation benchmark single perturbations",
                validation_scope="held-out perturbations in the same K562 benchmark",
            ),
            data_version="DeltaFactor:full_v1", code_version="2.0.0",
            warnings=["context_match_below_0.5", "excluded_from_formal_ranking"],
            limitations=["K562 predictions are not UC causal evidence.", "No extrapolation to genes outside the training condition set."],
        )
        return ToolExecution(result=result, evidence=[])

