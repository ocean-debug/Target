"""Deterministic best-practice reviewer; LLM output cannot waive these gates."""
from __future__ import annotations

from collections import defaultdict

from .contracts import (
    ClaimClass, CoverageStatus, EvidenceItem, ReviewerFinding, TaskSpec,
    ToolResult, ToolStatus,
)


class Reviewer:
    def review(self, task: TaskSpec, results: list[ToolResult], evidence: list[EvidenceItem]) -> list[ReviewerFinding]:
        findings: list[ReviewerFinding] = []
        tool_ids = {result.tool_run_id for result in results}
        evidence_ids = {item.evidence_id for item in evidence}
        for item in evidence:
            if item.tool_run_id not in tool_ids or not item.source.uri or not item.source_span:
                findings.append(ReviewerFinding(
                    severity="blocking", category="missing_provenance",
                    message=f"Evidence {item.evidence_id} lacks a valid tool/source/span chain.",
                    related_ids=[item.evidence_id, item.tool_run_id], required_action="Repair or remove the evidence before reporting.",
                ))
            if item.context_match_score < 0.5:
                findings.append(ReviewerFinding(
                    severity="major", category="context_mismatch",
                    message=f"Evidence {item.evidence_id} has context match {item.context_match_score:.2f} and cannot enter formal ranking.",
                    related_ids=[item.evidence_id], required_action="Exclude from formal score and retain only as exploratory context.",
                ))
            causal_words = ("causes", "causal evidence", "drives disease", "proves")
            if item.claim_class != ClaimClass.INFERRED and any(word in item.statement.lower() for word in causal_words):
                findings.append(ReviewerFinding(
                    severity="major", category="causal_overreach",
                    message=f"Evidence {item.evidence_id} uses causal language beyond its evidence class.",
                    related_ids=[item.evidence_id], required_action="Downgrade language or add a valid causal design.",
                ))
        for result in results:
            missing = set(result.evidence_ids) - evidence_ids
            if missing:
                findings.append(ReviewerFinding(
                    severity="blocking", category="missing_provenance",
                    message=f"Tool {result.tool_run_id} references missing EvidenceItems.",
                    related_ids=[result.tool_run_id, *sorted(missing)], required_action="Restore the missing EvidenceItems.",
                ))
            if result.status == ToolStatus.FAILED:
                findings.append(ReviewerFinding(
                    severity="major", category="tool_failure",
                    message=f"Tool {result.tool_name} failed: {result.error}", related_ids=[result.tool_run_id],
                    required_action="Retry within budget or mark the corresponding evidence dimension as missing.",
                ))
            if result.coverage_status == CoverageStatus.NOT_COVERED:
                severity = "blocking" if result.tool_name in {"uc_omics_snapshot", "mch_causal_gold"} else "major"
                findings.append(ReviewerFinding(
                    severity=severity, category="coverage_gap",
                    message=f"Tool {result.tool_name} does not cover the requested context.", related_ids=[result.tool_run_id],
                    required_action="Request matching input/data; do not describe this step as complete.",
                ))
            elif result.coverage_status == CoverageStatus.PARTIAL:
                severity = "minor" if result.tool_name == "deltafactor" else "major"
                findings.append(ReviewerFinding(
                    severity=severity, category="coverage_gap",
                    message=f"Tool {result.tool_name} has partial coverage.", related_ids=[result.tool_run_id],
                    required_action="Expose uncovered genes/context as an evidence gap.",
                ))
            if result.context_match_score < 0.5:
                severity = "minor" if result.outputs.get("formal_score_eligible") is False else "major"
                findings.append(ReviewerFinding(
                    severity=severity, category="context_mismatch",
                    message=f"Tool {result.tool_name} context match is {result.context_match_score:.2f}.",
                    related_ids=[result.tool_run_id], required_action="Exclude low-match outputs from formal ranking.",
                ))

        directions: dict[str, set[str]] = defaultdict(set)
        ids_by_gene: dict[str, list[str]] = defaultdict(list)
        for item in evidence:
            if item.gene_symbol and item.effect_direction in {"increase", "decrease"} and item.stance.value in {"supports", "refutes", "mixed"}:
                directions[item.gene_symbol].add(item.effect_direction)
                ids_by_gene[item.gene_symbol].append(item.evidence_id)
        for gene, values in directions.items():
            if len(values) > 1:
                findings.append(ReviewerFinding(
                    severity="major", category="conflicting_evidence",
                    message=f"{gene} has opposing effect directions across contexts.",
                    related_ids=ids_by_gene[gene], required_action="Keep both directions and resolve by tissue, cell, assay and perturbation context.",
                ))
        return self._deduplicate(findings)

    @staticmethod
    def _deduplicate(findings: list[ReviewerFinding]) -> list[ReviewerFinding]:
        unique = {}
        for finding in findings:
            key = (finding.severity, finding.category, finding.message, tuple(finding.related_ids))
            unique[key] = finding
        return list(unique.values())

