"""Transparent six-dimensional ranking; total score is never a success probability."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import ClaimClass, EvidenceItem, ScoreBreakdown, Stance, ToolResult


WEIGHTS = {
    "human_genetics": 25.0,
    "disease_omics": 20.0,
    "perturbation": 20.0,
    "mechanism": 15.0,
    "druggability": 10.0,
    "safety_translation": 10.0,
}


@dataclass
class RankedTarget:
    gene: str
    scores: ScoreBreakdown
    evidence_ids: list[str]
    supporting_ids: list[str]
    opposing_ids: list[str]
    safety_blockers: list[str]
    evidence_gaps: list[str]
    matched_drugs: list[dict[str, Any]]
    decision: str


def _clamp(value: float, high: float) -> float:
    return round(max(0.0, min(high, value)), 4)


def _phase_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").lower()
    for digit in ("4", "3", "2", "1"):
        if digit in text:
            return float(digit)
    for token, score in (("iv", 4), ("iii", 3), ("ii", 2), ("i", 1), ("approved", 4)):
        if token in text:
            return float(score)
    return 0.0


def rank_targets(candidates: list[str], evidence: list[EvidenceItem], results: list[ToolResult]) -> list[RankedTarget]:
    by_gene: dict[str, list[EvidenceItem]] = {gene: [] for gene in candidates}
    for item in evidence:
        if item.gene_symbol in by_gene:
            by_gene[item.gene_symbol].append(item)
    ot_by_gene: dict[str, dict[str, Any]] = {}
    for result in results:
        if result.tool_name == "open_targets":
            ot_by_gene.update({row["gene"]: row for row in result.outputs.get("associations", [])})

    ranked = []
    for gene in candidates:
        items = by_gene[gene]
        formal = [item for item in items if item.context_match_score >= 0.5]
        genetics = 0.0
        omics = 0.0
        perturb = 0.0
        mechanism = 0.0
        druggability = 0.0
        safety = 0.0
        gaps = []
        blockers = []
        matched_drugs = ot_by_gene.get(gene, {}).get("known_drugs", [])
        tractability = ot_by_gene.get(gene, {}).get("tractability", [])

        for item in formal:
            context = item.context_match_score
            if "genetic_score" in item.effect:
                genetics = max(genetics, WEIGHTS["human_genetics"] * float(item.effect["genetic_score"]) * context)
            if "legacy_disease_strength_0_60" in item.effect:
                normalized = float(item.effect["legacy_disease_strength_0_60"]) / 60.0
                omics = max(omics, WEIGHTS["disease_omics"] * normalized * context)
            if item.claim_class == ClaimClass.OBSERVED and "disease_alignment" in item.effect:
                alignment = abs(float(item.effect["disease_alignment"]))
                perturb = max(perturb, (8.0 + min(12.0, alignment / 0.1 * 12.0)) * context)
            if item.claim_class == ClaimClass.PREDICTED:
                perturb = max(perturb, min(WEIGHTS["perturbation"] / 2.0, 10.0 * context))

        has_omics = any("legacy_disease_strength_0_60" in item.effect for item in formal)
        has_observed_perturb = any(item.claim_class == ClaimClass.OBSERVED and "disease_alignment" in item.effect for item in formal)
        has_literature = any(item.claim_class == ClaimClass.FACT and "europepmc" in item.source.uri.lower() for item in formal)
        if has_omics and has_observed_perturb:
            mechanism += 8.0
        if has_literature:
            mechanism += 4.0
        if genetics > 0 and has_omics:
            mechanism += 3.0
        mechanism = min(WEIGHTS["mechanism"], mechanism)
        if matched_drugs:
            max_phase = max(_phase_value(drug.get("phase")) for drug in matched_drugs)
            druggability = min(10.0, 4.0 + max_phase * 1.5)
        elif any(item.get("value") for item in tractability):
            druggability = 4.0
        if not any("safety" in item.effect for item in formal):
            gaps.append("No matched, source-grounded safety evidence was retrieved.")
        if genetics == 0:
            gaps.append("No qualifying human-genetic evidence in the current store.")
        if not has_observed_perturb:
            gaps.append("No matched-context measured perturbation evidence for this target.")
        if not has_literature:
            gaps.append("No span-validated literature claim for this target.")
        if not matched_drugs:
            gaps.append("No known drug was returned in the current Open Targets result.")
        opposing = [item.evidence_id for item in items if item.stance in {Stance.REFUTES, Stance.MIXED}]
        supporting = [item.evidence_id for item in items if item.stance == Stance.SUPPORTS]
        if opposing:
            blockers.append("Opposing or mixed evidence is retained and requires context-specific review.")
        safety_events = [str(item.effect["safety"].get("event") or item.effect["safety"].get("eventId"))
                         for item in items if "safety" in item.effect]
        blockers.extend(f"Open Targets safety liability: {event}" for event in safety_events)

        scores = ScoreBreakdown(
            human_genetics=_clamp(genetics, 25), disease_omics=_clamp(omics, 20),
            perturbation=_clamp(perturb, 20), mechanism=_clamp(mechanism, 15),
            druggability=_clamp(druggability, 10), safety_translation=_clamp(safety, 10),
            total=_clamp(genetics + omics + perturb + mechanism + druggability + safety, 100),
        )
        independent = sum([genetics > 0, has_omics, has_observed_perturb, has_literature, bool(matched_drugs)])
        gate = genetics > 0 or has_observed_perturb
        if blockers:
            decision = "CONDITIONAL_GO" if independent >= 2 else "INSUFFICIENT_EVIDENCE"
        elif independent >= 2 and gate:
            decision = "GO"
        elif independent >= 2:
            decision = "CONDITIONAL_GO"
        else:
            decision = "INSUFFICIENT_EVIDENCE"
        ranked.append(RankedTarget(
            gene=gene, scores=scores, evidence_ids=[item.evidence_id for item in items],
            supporting_ids=supporting, opposing_ids=opposing, safety_blockers=blockers,
            evidence_gaps=gaps, matched_drugs=matched_drugs, decision=decision,
        ))
    ranked.sort(key=lambda row: (-row.scores.total, row.gene))
    return ranked
