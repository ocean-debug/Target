"""Task-specific candidate-universe policies shared by both runtimes."""
from __future__ import annotations

from collections.abc import Callable

from .contracts import CoverageStatus, EvidenceItem, Stance, TaskSpec, ToolResult, ToolStatus


MergeCandidates = Callable[[list[str], ToolResult, int], list[str]]


def initial_candidate_genes(task: TaskSpec) -> list[str]:
    if task.task_type == "gwas_locus_to_target":
        return []
    return list(task.candidate_genes)


def formal_gwas_candidates(
    results: list[ToolResult],
    evidence: list[EvidenceItem],
    minimum_coloc_pp4: float,
    max_candidates: int,
) -> list[str]:
    extraction = next(
        (result for result in reversed(results) if result.tool_name == "genetics_candidate_extraction"),
        None,
    )
    if (
        extraction is None
        or extraction.status not in {ToolStatus.SUCCESS, ToolStatus.PARTIAL}
        or extraction.coverage_status not in {CoverageStatus.COVERED, CoverageStatus.PARTIAL}
        or extraction.outputs.get("covered") is not True
    ):
        return []

    by_run_id = {result.tool_run_id: result for result in results}
    lineage = {}
    for input_key, expected_tool in (
        ("genetics_input_audit_tool_run_id", "genetics_input_audit"),
        ("fine_mapping_tool_run_id", "fine_mapping_audit"),
        ("colocalization_tool_run_id", "eqtl_colocalization_audit"),
    ):
        referenced_id = extraction.inputs.get(input_key)
        if not isinstance(referenced_id, str):
            return []
        referenced = by_run_id.get(referenced_id)
        if (
            referenced is None
            or referenced.tool_name != expected_tool
            or referenced.status not in {ToolStatus.SUCCESS, ToolStatus.PARTIAL}
            or referenced.coverage_status not in {CoverageStatus.COVERED, CoverageStatus.PARTIAL}
            or referenced.outputs.get("covered") is not True
        ):
            return []
        lineage[expected_tool] = referenced

    input_assets = lineage["genetics_input_audit"].outputs.get("assets", [])
    credible_sets = lineage["fine_mapping_audit"].outputs.get("credible_sets", [])
    coloc_rows = lineage["eqtl_colocalization_audit"].outputs.get("colocalizations", [])
    if (
        not isinstance(input_assets, list)
        or not any(isinstance(row, dict) and row.get("kind") == "gwas_summary_statistics" for row in input_assets)
        or not isinstance(credible_sets, list)
        or not isinstance(coloc_rows, list)
        or lineage["eqtl_colocalization_audit"].inputs.get("genetics_input_audit_tool_run_id")
        != lineage["genetics_input_audit"].tool_run_id
        or lineage["eqtl_colocalization_audit"].inputs.get("fine_mapping_tool_run_id")
        != lineage["fine_mapping_audit"].tool_run_id
    ):
        return []
    evidence_by_id = {item.evidence_id: item for item in evidence}
    output_candidates = extraction.outputs.get("candidate_genes", [])
    if not isinstance(output_candidates, list):
        return []
    output_candidate_set = {str(gene).upper() for gene in output_candidates if gene}
    accepted: dict[str, tuple[int, float, float]] = {}
    for raw_gene in extraction.candidate_genes:
        gene = str(raw_gene).upper()
        if not gene or gene not in output_candidate_set:
            continue
        matching_items = [
            evidence_by_id[evidence_id]
            for evidence_id in extraction.evidence_ids
            if evidence_id in evidence_by_id
            and evidence_by_id[evidence_id].tool_run_id == extraction.tool_run_id
            and (evidence_by_id[evidence_id].gene_symbol or "").upper() == gene
        ]
        accepted_items = [
            item for item in matching_items
            if item.genetic_evidence is not None
            and item.genetic_evidence.formal_score_eligible
            and item.context_match_score >= 0.5
            and item.stance == Stance.SUPPORTS
            and item.genetic_evidence.strength >= minimum_coloc_pp4
            and any(_coloc_row_matches(
                row, gene, item, minimum_coloc_pp4, input_assets, credible_sets,
            ) for row in coloc_rows)
        ]
        if accepted_items:
            independent_loci = {
                (item.genetic_evidence.study_id, item.genetic_evidence.locus_id)
                for item in accepted_items if item.genetic_evidence is not None
            }
            accepted[gene] = (
                len(independent_loci),
                max(item.context_match_score for item in accepted_items),
                max(item.genetic_evidence.strength for item in accepted_items if item.genetic_evidence),
            )
    return sorted(
        accepted,
        key=lambda gene: (
            -accepted[gene][0], -accepted[gene][1], -accepted[gene][2], gene,
        ),
    )[:max_candidates]


def merge_candidates_for_task(
    task: TaskSpec,
    current: list[str],
    result: ToolResult,
    limit: int,
    default_merge: MergeCandidates,
    results: list[ToolResult],
    evidence: list[EvidenceItem],
    minimum_coloc_pp4: float,
) -> list[str]:
    if task.task_type != "gwas_locus_to_target":
        return default_merge(current, result, limit)
    if result.tool_name == "genetics_candidate_extraction":
        return formal_gwas_candidates(
            results, evidence, minimum_coloc_pp4, limit,
        )
    return list(current)[:limit]


__all__ = ["formal_gwas_candidates", "initial_candidate_genes", "merge_candidates_for_task"]


def _coloc_row_matches(
    row: object,
    gene: str,
    item: EvidenceItem,
    minimum_coloc_pp4: float,
    input_assets: list[object],
    credible_sets: list[object],
) -> bool:
    if not isinstance(row, dict) or item.genetic_evidence is None:
        return False
    try:
        pp4 = float(row.get("pp4", -1))
    except (TypeError, ValueError):
        return False
    genetic = item.genetic_evidence
    gwas_study_id = row.get("gwas_study_id") or row.get("study_id")
    input_matches = any(
        isinstance(asset, dict)
        and asset.get("kind") == "gwas_summary_statistics"
        and asset.get("study_id") == gwas_study_id
        for asset in input_assets
    )
    fine_mapping_matches = any(
        isinstance(credible_set, dict)
        and credible_set.get("formal_score_eligible") is True
        and credible_set.get("study_id") == gwas_study_id
        and credible_set.get("locus_id") == row.get("locus_id")
        and credible_set.get("credible_set_id") == row.get("signal_id")
        for credible_set in credible_sets
    )
    return (
        input_matches
        and fine_mapping_matches
        and row.get("formal_score_eligible") is True
        and str(row.get("gene") or "").upper() == gene
        and row.get("study_id") == genetic.study_id
        and row.get("locus_id") == genetic.locus_id
        and row.get("signal_id") == genetic.signal_id
        and abs(pp4 - genetic.strength) <= 1e-12
        and pp4 >= minimum_coloc_pp4
    )
