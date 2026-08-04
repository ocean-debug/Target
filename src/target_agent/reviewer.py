"""Deterministic best-practice reviewer; LLM output cannot waive these gates."""
from __future__ import annotations

from collections import defaultdict
import json
from typing import Any

from pydantic import ValidationError

from .contracts import (
    ClaimClass, CoverageStatus, EvidenceItem, ReviewerFinding, TaskSpec,
    ToolResult, ToolStatus,
)
from .llm import LLMUnavailable, StepClient


class Reviewer:
    def __init__(self, client: StepClient | None = None, settings=None):
        self.client = client
        self.last_backend = "deterministic"
        self._lora = None
        if settings is not None and getattr(settings, "reviewer_lora_adapter", None):
            from .reviewer_lora import LoRAReviewerBackend
            self._lora = LoRAReviewerBackend(settings.reviewer_lora_base, settings.reviewer_lora_adapter)

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
                severity = "blocking" if task.task_type == "trait_mechanism" and result.tool_name == "mch_causal_gold" else "major"
                findings.append(ReviewerFinding(
                    severity=severity, category="coverage_gap",
                    message=f"Tool {result.tool_name} does not cover the requested context.", related_ids=[result.tool_run_id],
                    required_action="Request matching input/data; do not describe this step as complete.",
                ))
            elif result.coverage_status == CoverageStatus.PARTIAL:
                severity = "minor" if result.outputs.get("formal_score_eligible") is False else "major"
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
            for numeric_error in result.outputs.get("numeric_validation_errors", []):
                findings.append(ReviewerFinding(
                    severity="blocking", category="numeric_error",
                    message=f"Tool {result.tool_name} emitted an invalid numeric value: {numeric_error}",
                    related_ids=[result.tool_run_id],
                    required_action="Remove or recompute the invalid numeric output before reporting.",
                ))
            if result.tool_name == "geo_metadata_audit":
                selected = result.outputs.get("selected_datasets", [])
                for rejected in result.outputs.get("rejected_datasets", []):
                    candidate = rejected.get("candidate", {})
                    reasons = candidate.get("exclusion_reasons", [])
                    findings.append(ReviewerFinding(
                        severity="minor" if selected else "major",
                        category="dataset_ineligibility",
                        message=(
                            f"GEO dataset {candidate.get('accession', 'unknown')} was rejected: "
                            + ", ".join(reasons or ["unspecified eligibility failure"])
                        ),
                        related_ids=[result.tool_run_id],
                        required_action="Select the next eligible dataset or retain the omics dimension as a documented gap.",
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
        findings.extend(self._lora_findings(task, results, evidence))
        findings.extend(self._llm_findings(task, results, evidence))
        return self._deduplicate(findings)

    def _lora_findings(
        self, task: TaskSpec, results: list[ToolResult], evidence: list[EvidenceItem]
    ) -> list[ReviewerFinding]:
        """Local LoRA confirmation layer; preferred over the hosted Step path when configured."""
        if self._lora is None:
            return []
        try:
            findings = self._lora.findings(task, results, evidence)
            self.last_backend = self._lora.name
            return findings
        except Exception:  # adapter failure must never block deterministic review
            self.last_backend = "deterministic:lora_unavailable"
            return []

    def _llm_findings(
        self, task: TaskSpec, results: list[ToolResult], evidence: list[EvidenceItem]
    ) -> list[ReviewerFinding]:
        if not self.client or self._lora is not None:
            if self._lora is None:
                self.last_backend = "deterministic"
            return []
        allowed_ids = {result.tool_run_id for result in results} | {item.evidence_id for item in evidence}
        payload: dict[str, Any] = {
            "task": task.model_dump(mode="json"),
            "tool_results": [
                {
                    "tool_run_id": result.tool_run_id, "tool_name": result.tool_name,
                    "status": result.status.value, "coverage_status": result.coverage_status.value,
                    "context_match_score": result.context_match_score,
                    "warnings": result.warnings, "limitations": result.limitations,
                    "outputs": {
                        key: value for key, value in result.outputs.items()
                        if key in {"selection_trace", "formal_score_eligible", "analysis_stage", "numeric_validation_errors"}
                    },
                }
                for result in results
            ],
            "evidence": [
                {
                    "evidence_id": item.evidence_id, "gene": item.gene_symbol,
                    "claim_class": item.claim_class.value, "statement": item.statement,
                    "context": item.context.model_dump(mode="json"),
                    "context_match_score": item.context_match_score,
                }
                for item in evidence[:100]
            ],
        }
        system = (
            "You are a life-science best-practice reviewer. Add findings only; never waive deterministic gates. "
            "Return JSON with a findings array. Each item must contain severity (blocking, major, or minor), "
            "category, message, related_ids, and required_action. Flag metadata ambiguity, causal overreach, "
            "context mismatch, conflicting evidence, and missing validation. Use only supplied IDs."
        )
        try:
            raw = self.client.json_completion(system, json.dumps(payload, ensure_ascii=False))
            reviewed: list[ReviewerFinding] = []
            for item in list(raw.get("findings") or [])[:10]:
                finding = ReviewerFinding.model_validate(item)
                if set(finding.related_ids).issubset(allowed_ids):
                    reviewed.append(finding)
            self.last_backend = f"step:{self.client.model}"
            return reviewed
        except (LLMUnavailable, ValidationError, ValueError, TypeError, json.JSONDecodeError):
            self.last_backend = "deterministic:step_unavailable_or_invalid"
            return []

    @staticmethod
    def _deduplicate(findings: list[ReviewerFinding]) -> list[ReviewerFinding]:
        unique = {}
        for finding in findings:
            key = (finding.severity, finding.category, finding.message, tuple(finding.related_ids))
            unique[key] = finding
        return list(unique.values())
