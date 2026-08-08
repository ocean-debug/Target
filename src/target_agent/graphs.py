"""Mechanistic evidence graph construction and pattern-aware evidence synthesis.

The graph is a deterministic projection of the durable Evidence Store:

- entity nodes: disease, locus, variant, gene, cell state (tissue/cell type), drug;
- lane nodes: aggregated evidence layers (genetics / omics / perturbation / drug /
  literature / safety) with per-gene membership edges;
- pattern links: cross-layer connections suggested by an approved strategy
  pattern distilled from recent high-impact papers. Pattern links are INFERRED
  strategy hypotheses, never evidence for the current disease. They are withheld
  when the two lanes depend on the same source lineage or when the gene has an
  unresolved direction conflict.
"""
from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import Any, Iterable

from pydantic import ValidationError

from .contracts import (
    CausalGraph, ClaimClass, EvidenceContext, EvidenceItem, GraphEdge, GraphNode,
    TaskSpec,
)
from .paper_strategy import BestPracticePattern, StrategyPattern

EVIDENCE_LANES: tuple[str, ...] = (
    "genetics", "omics", "perturbation", "drug", "literature", "safety",
)
MIN_LINK_CONTEXT = 0.5
_MAX_EVIDENCE_IDS_PER_EDGE = 12


@dataclass
class EvidenceSynthesisResult:
    """Graph plus the deterministic quality-gate findings that produced it."""

    graph: CausalGraph
    findings: list[dict[str, Any]]
    lane_coverage: dict[str, dict[str, list[str]]]
    pattern_links: list[dict[str, Any]]
    paper_links: list[dict[str, Any]] = field(default_factory=list)


def _parse_pattern(raw: StrategyPattern | BestPracticePattern | dict[str, Any]) -> StrategyPattern | None:
    if isinstance(raw, StrategyPattern):
        return raw
    if not isinstance(raw, dict):
        return None
    try:
        return StrategyPattern.model_validate(raw)
    except ValidationError:
        try:
            return BestPracticePattern.model_validate(raw)
        except ValidationError:
            return None


def _context_key(item: EvidenceItem) -> tuple[str, str, str, str]:
    ctx = item.context
    return (
        str(ctx.tissue or ""), str(ctx.cell_type or ""),
        str(ctx.assay or ""), str(ctx.perturbation_type or ""),
    )


def _lineage_key(item: EvidenceItem) -> str:
    genetic = item.genetic_evidence
    study = item.context.study_id or (genetic.study_id if genetic else None) or ""
    dataset = str((item.effect or {}).get("accession") or "")
    return "|".join((str(item.source.source_id or ""), str(study), dataset, item.tool_run_id))


def infer_evidence_lane(item: EvidenceItem) -> str | None:
    """Deterministic lane inference from the evidence contract itself.

    The inference never depends on prose: it reads structured fields (genetic
    payload, perturbation type, effect keys, source section) and only falls
    back to the literature lane when nothing else applies.
    """
    effect = item.effect or {}
    if "safety" in effect:
        return "safety"
    if "drug" in effect or "phase" in effect or "trial_id" in effect:
        return "drug"
    if item.genetic_evidence is not None:
        return "genetics"
    if "somatic" in effect or "mutation" in effect:
        return "genetics"
    if item.context.perturbation_type:
        return "perturbation"
    if any(key in effect for key in ("log2fc", "omics_strength", "padj", "fdr", "accession")):
        return "omics"
    assay = (item.context.assay or "").lower()
    if any(token in assay for token in (
        "rna-seq", "scrna", "sc-rna", "atac", "chip", "expression",
        "proteomic", "metabolomic", "crispr",
    )):
        return "omics"
    section = (item.source.section or "").lower()
    if "drug" in section or "clinical" in section:
        return "drug"
    if "safety" in section:
        return "safety"
    return "literature"


def _direction_conflicts(
    evidence: list[EvidenceItem], evidence_by_id: dict[str, EvidenceItem],
) -> tuple[set[str], list[dict[str, Any]]]:
    directions: dict[str, dict[str, list[str]]] = {}
    for item in evidence:
        gene = item.gene_symbol
        direction = item.effect_direction
        if not gene or direction not in {"increase", "decrease"}:
            continue
        directions.setdefault(gene, {}).setdefault(direction, []).append(item.evidence_id)
    conflict_genes: set[str] = set()
    findings: list[dict[str, Any]] = []
    for gene, by_direction in directions.items():
        increase = by_direction.get("increase", [])
        decrease = by_direction.get("decrease", [])
        if not increase or not decrease:
            continue
        conflict_genes.add(gene)
        contexts = {
            _context_key(evidence_by_id[eid])
            for eid in (*increase[:5], *decrease[:5])
            if eid in evidence_by_id
        }
        split = len(contexts) > 1
        findings.append({
            "finding_id": f"graph-direction-{gene.lower()}",
            "category": "conflicting_evidence",
            "severity": "major" if split else "blocking",
            "related_ids": [increase[0], decrease[0]],
            "subject": {"gene": gene},
            "message": (
                f"{gene} has opposing effect directions across evidence items"
                + (
                    " in different tissue/cell/assay contexts; re-bind each evidence "
                    "to its same-scope sub-context before ranking."
                    if split
                    else "; resolve by tissue, cell, assay and perturbation context before ranking."
                )
            ),
        })
    return conflict_genes, findings


def _dependent_lane_pairs(
    lane_coverage: dict[str, dict[str, list[str]]],
    evidence_by_id: dict[str, EvidenceItem],
) -> tuple[set[tuple[str, str, str]], list[dict[str, Any]]]:
    dependent: set[tuple[str, str, str]] = set()
    findings: list[dict[str, Any]] = []
    for gene, lanes in lane_coverage.items():
        lane_names = [lane for lane in EVIDENCE_LANES if lane in lanes]
        for index, lane_a in enumerate(lane_names):
            for lane_b in lane_names[index + 1:]:
                items_a = [
                    evidence_by_id[eid] for eid in lanes[lane_a]
                    if eid in evidence_by_id
                ]
                items_b = [
                    evidence_by_id[eid] for eid in lanes[lane_b]
                    if eid in evidence_by_id
                ]
                runs_a = {item.tool_run_id for item in items_a}
                runs_b = {item.tool_run_id for item in items_b}
                shared_run = runs_a & runs_b
                lineages_a = {_lineage_key(item) for item in items_a}
                lineages_b = {_lineage_key(item) for item in items_b}
                shared_lineage = lineages_a & lineages_b
                if not shared_run and not shared_lineage:
                    continue
                dependent.add((gene, lane_a, lane_b))
                shared_key = (
                    f"tool run {next(iter(shared_run))}"
                    if shared_run else next(iter(shared_lineage))
                )
                findings.append({
                    "finding_id": f"graph-dependence-{gene.lower()}-{lane_a}-{lane_b}",
                    "category": "evidence_dependence",
                    "severity": "major",
                    "related_ids": [lanes[lane_a][0], lanes[lane_b][0]],
                    "subject": {"gene": gene, "source_lane": lane_a, "target_lane": lane_b},
                    "message": (
                        f"Pattern links between {lane_a} and {lane_b} for {gene} are withheld: "
                        f"both lanes share {shared_key}, so independent support "
                        "is not established."
                    ),
                })
    return dependent, findings


def _build_entity_graph(
    task: TaskSpec,
    evidence: list[EvidenceItem],
    genes: list[str],
    lane_by_id: dict[str, str | None],
    lane_coverage: dict[str, dict[str, list[str]]],
    evidence_by_id: dict[str, EvidenceItem],
) -> tuple[dict[str, GraphNode], list[GraphEdge]]:
    disease = task.context.disease or "disease"
    nodes: dict[str, GraphNode] = {
        "disease": GraphNode(
            node_id="disease", node_type="disease", label=disease,
            attributes={
                "organism": task.context.organism,
                "tissue": task.context.tissue,
                "cell_type": task.context.cell_type,
                "disease_stage": task.context.disease_stage,
            },
        ),
    }
    edges: list[GraphEdge] = []
    seen_genes: set[str] = set()
    for gene in genes:
        clean = (gene or "").strip()
        if not clean or clean in seen_genes:
            continue
        seen_genes.add(clean)
        nodes[f"gene:{clean}"] = GraphNode(node_id=f"gene:{clean}", node_type="gene", label=clean)

    cell_state_nodes: dict[tuple[str, str], str] = {}
    cell_state_evidence: dict[str, list[str]] = {}
    drug_nodes: dict[str, str] = {}

    for item in evidence:
        gene = (item.gene_symbol or "").strip()
        lane = lane_by_id.get(item.evidence_id)
        if not gene or gene not in seen_genes or not lane:
            continue
        genetic = item.genetic_evidence
        has_genetic_locus = bool(genetic and genetic.locus_id)
        if lane == "safety":
            edges.append(GraphEdge(
                source=f"gene:{gene}", target="disease", relation="safety_liability",
                evidence_ids=[item.evidence_id], claim_class=item.claim_class,
                weight=item.context_match_score,
                attributes={
                    "stance": item.stance.value, "lane": "safety", "safety_blocker": True,
                },
            ))
            continue
        if has_genetic_locus:
            locus_id = f"locus:{genetic.study_id}:{genetic.locus_id}:{genetic.signal_id or 'unresolved'}"
            nodes.setdefault(locus_id, GraphNode(
                node_id=locus_id, node_type="locus", label=genetic.locus_id,
                attributes={
                    "study_id": genetic.study_id, "signal_id": genetic.signal_id,
                    "genome_build": item.context.genome_build,
                    "causal_status": "not_established",
                },
            ))
            if genetic.variant_id:
                variant_id = (
                    f"variant:{genetic.study_id}:{item.context.genome_build or 'unknown'}:"
                    f"{genetic.variant_id}"
                )
                nodes.setdefault(variant_id, GraphNode(
                    node_id=variant_id, node_type="variant", label=genetic.variant_id,
                    attributes={"genome_build": item.context.genome_build},
                ))
                edges.append(GraphEdge(
                    source=variant_id, target=locus_id,
                    relation="statistical_signal_membership",
                    evidence_ids=[item.evidence_id], claim_class=ClaimClass.INFERRED,
                    weight=item.context_match_score,
                ))
            edges.append(GraphEdge(
                source=locus_id, target="disease", relation="human_genetic_association",
                evidence_ids=[item.evidence_id], claim_class=item.claim_class,
                weight=item.context_match_score,
            ))
            if genetic.formal_score_eligible:
                edges.append(GraphEdge(
                    source=locus_id, target=f"gene:{gene}",
                    relation="colocalization_shared_signal_hypothesis",
                    evidence_ids=[item.evidence_id], claim_class=ClaimClass.INFERRED,
                    weight=item.context_match_score,
                ))
        else:
            relation = {
                ClaimClass.FACT: "database_or_literature_association",
                ClaimClass.OBSERVED: "observed_context_association",
                ClaimClass.PREDICTED: "predicted_effect",
                ClaimClass.INFERRED: "agent_inference",
            }.get(item.claim_class, "agent_inference")
            edges.append(GraphEdge(
                source=f"gene:{gene}", target="disease", relation=relation,
                evidence_ids=[item.evidence_id], claim_class=item.claim_class,
                weight=item.context_match_score,
                attributes={
                    "stance": item.stance.value, "lane": lane,
                    "direction": item.effect_direction,
                },
            ))
        if lane == "drug":
            drug = item.effect.get("drug") if isinstance(item.effect.get("drug"), dict) else {}
            drug_id = str(drug.get("drugId") or drug.get("prefName") or f"drug-{item.evidence_id}")
            drug_key = f"drug:{drug_id}"
            if drug_key not in nodes:
                nodes[drug_key] = GraphNode(
                    node_id=drug_key, node_type="drug",
                    label=str(drug.get("prefName") or drug_id),
                    attributes={
                        "drug_id": str(drug.get("drugId") or ""),
                        "clinical_stage": drug.get("phase"),
                    },
                )
            edges.append(GraphEdge(
                source=f"gene:{gene}", target=drug_key, relation="known_drug_link",
                evidence_ids=[item.evidence_id], claim_class=item.claim_class,
                weight=item.context_match_score,
                attributes={"lane": "drug"},
            ))
        for layer, value in (("tissue", item.context.tissue), ("cell_type", item.context.cell_type)):
            if not value:
                continue
            key = (layer, value)
            cell_id = cell_state_nodes.get(key)
            if cell_id is None:
                cell_id = f"cell:{layer}:{value}"
                cell_state_nodes[key] = cell_id
                nodes[cell_id] = GraphNode(
                    node_id=cell_id, node_type="cell_state", label=value,
                    attributes={"layer": layer},
                )
            edges.append(GraphEdge(
                source=f"gene:{gene}", target=cell_id, relation="context_localization",
                evidence_ids=[item.evidence_id], claim_class=item.claim_class,
                weight=item.context_match_score,
                attributes={"lane": lane},
            ))
            cell_state_evidence.setdefault(cell_id, []).append(item.evidence_id)

    lane_present: dict[str, list[str]] = {}
    for gene, lanes in lane_coverage.items():
        if gene not in seen_genes:
            continue
        for lane in lanes:
            lane_present.setdefault(lane, []).append(gene)
    for lane in EVIDENCE_LANES:
        genes_in_lane = lane_present.get(lane)
        if not genes_in_lane:
            continue
        lane_id = f"lane:{lane}"
        nodes[lane_id] = GraphNode(
            node_id=lane_id, node_type="lane", label=lane,
            attributes={"gene_count": len(genes_in_lane)},
        )
    for gene, lanes in lane_coverage.items():
        if gene not in seen_genes:
            continue
        for lane, ids in lanes.items():
            lane_id = f"lane:{lane}"
            if lane_id not in nodes:
                continue
            items = [evidence_by_id[eid] for eid in ids if eid in evidence_by_id]
            if not items:
                continue
            max_context = max((it.context_match_score for it in items), default=0.0)
            classes = sorted({it.claim_class.value for it in items})
            edges.append(GraphEdge(
                source=f"gene:{gene}", target=lane_id, relation="has_evidence_in",
                evidence_ids=ids[:_MAX_EVIDENCE_IDS_PER_EDGE],
                claim_class=ClaimClass.OBSERVED,
                weight=max_context,
                attributes={
                    "item_claim_classes": classes, "evidence_count": len(ids),
                },
            ))
    for lane, genes_in_lane in lane_present.items():
        if lane == "safety":
            continue
        all_ids: list[str] = []
        for gene in genes_in_lane:
            all_ids.extend(lane_coverage.get(gene, {}).get(lane, []))
        items = [evidence_by_id[eid] for eid in all_ids if eid in evidence_by_id]
        if not items:
            continue
        edges.append(GraphEdge(
            source=f"lane:{lane}", target="disease",
            relation="evidence_lane_supports_disease",
            evidence_ids=all_ids[:_MAX_EVIDENCE_IDS_PER_EDGE],
            claim_class=ClaimClass.INFERRED,
            weight=max((it.context_match_score for it in items), default=0.0),
            attributes={"lane": lane, "gene_count": len(genes_in_lane)},
        ))
    for cell_id, evidence_ids in cell_state_evidence.items():
        items = [evidence_by_id[eid] for eid in evidence_ids if eid in evidence_by_id]
        if not items:
            continue
        edges.append(GraphEdge(
            source=cell_id, target="disease", relation="disease_context_relevance",
            evidence_ids=evidence_ids[:_MAX_EVIDENCE_IDS_PER_EDGE],
            claim_class=ClaimClass.INFERRED,
            weight=max((it.context_match_score for it in items), default=0.0),
        ))
    return nodes, edges


def _build_pattern_links(
    patterns: list[StrategyPattern],
    genes: list[str],
    lane_coverage: dict[str, dict[str, list[str]]],
    evidence_by_id: dict[str, EvidenceItem],
    dependent_pairs: set[tuple[str, str, str]],
    conflict_genes: set[str],
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for gene in genes:
        clean = (gene or "").strip()
        if not clean or clean in conflict_genes:
            continue
        lanes = lane_coverage.get(clean, {})
        for pattern in patterns:
            for link in pattern.evidence_links:
                src_ids = lanes.get(link.source_lane, [])
                tgt_ids = lanes.get(link.target_lane, [])
                src_items = [
                    evidence_by_id[eid] for eid in src_ids
                    if eid in evidence_by_id
                    and evidence_by_id[eid].context_match_score >= MIN_LINK_CONTEXT
                ]
                tgt_items = [
                    evidence_by_id[eid] for eid in tgt_ids
                    if eid in evidence_by_id
                    and evidence_by_id[eid].context_match_score >= MIN_LINK_CONTEXT
                ]
                if not src_items or not tgt_items:
                    continue
                if (clean, link.source_lane, link.target_lane) in dependent_pairs:
                    continue
                if (clean, link.target_lane, link.source_lane) in dependent_pairs:
                    continue
                key = (clean, pattern.pattern_id, link.source_lane, link.target_lane)
                if key in seen:
                    continue
                seen.add(key)
                src_best = max(src_items, key=lambda item: item.context_match_score)
                tgt_best = max(tgt_items, key=lambda item: item.context_match_score)
                links.append({
                    "gene": clean,
                    "pattern_id": pattern.pattern_id,
                    "pattern_name": pattern.name,
                    "link_id": link.link_id,
                    "link_type": link.link_type,
                    "source_lane": link.source_lane,
                    "target_lane": link.target_lane,
                    "evidence_ids": [src_best.evidence_id, tgt_best.evidence_id],
                    "weight": min(src_best.context_match_score, tgt_best.context_match_score),
                    "decision_rule": link.decision_rule,
                    "why_this_link": link.why_this_link,
                    "independence_note": link.independence_note,
                })
    return links


def _build_paper_strategy_links(
    paper_evidence: list[dict[str, Any]],
    genes: list[str],
) -> tuple[list[dict[str, Any]], dict[str, GraphNode], list[GraphEdge]]:
    """Project bounded paper-RAG hits as explicit strategy-hint nodes/edges.

    Paper hits are strategy context distilled from public abstracts, never
    evidence for the current disease: they are marked strategy_only with
    weight 0 and INFERRED, and they never touch lane coverage, conflicts,
    pattern links or ranking. Gene mention matching is deterministic and
    token-boundary based; malformed rows and unknown genes are skipped.
    """
    known = {gene.strip() for gene in genes if gene and gene.strip()}
    links: list[dict[str, Any]] = []
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    seen: set[tuple[str, str]] = set()
    for raw in paper_evidence or ():
        if not isinstance(raw, dict):
            continue
        chunk_id = str(raw.get("chunk_id") or "")
        pmid = str(raw.get("pmid") or "")
        if not chunk_id or not pmid:
            continue
        title = str(raw.get("title") or "")[:200]
        text_hay = " ".join(part for part in (title, str(raw.get("snippet") or ""))).lower()
        matched = [
            gene for gene in known
            if re.search(
                r"(?<![a-z0-9])" + re.escape(gene.lower()) + r"(?![a-z0-9])",
                text_hay,
            )
        ]
        if not matched:
            continue
        node_id = "strategy:paper:" + chunk_id
        nodes.setdefault(node_id, GraphNode(
            node_id=node_id,
            node_type="strategy_paper",
            label=title[:80] or ("paper " + pmid),
            attributes={
                "chunk_id": chunk_id,
                "pmid": pmid,
                "journal": str(raw.get("journal") or ""),
                "year": raw.get("year"),
                "doi": raw.get("doi"),
                "lane_tags": sorted({str(tag) for tag in (raw.get("lane_tags") or ())}),
                "strategy_only": True,
                "not_evidence": True,
                "role": "paper_rag_strategy_hint",
            },
        ))
        score = round(float(raw.get("score") or 0.0), 2)
        for gene in matched:
            key = (gene, chunk_id)
            if key in seen:
                continue
            seen.add(key)
            links.append({
                "gene": gene,
                "chunk_id": chunk_id,
                "pmid": pmid,
                "title": title,
                "journal": str(raw.get("journal") or ""),
                "year": raw.get("year"),
                "lane_tags": sorted({str(tag) for tag in (raw.get("lane_tags") or ())}),
                "score": score,
                "strategy_hint_not_evidence": True,
            })
            edges.append(GraphEdge(
                source="gene:" + gene,
                target=node_id,
                relation="paper_strategy_hint",
                evidence_ids=[],
                claim_class=ClaimClass.INFERRED,
                weight=0.0,
                attributes={
                    "strategy_only": True,
                    "not_evidence": True,
                    "role": "paper_rag_strategy_hint",
                    "rag_score": score,
                },
            ))
    return links, nodes, edges


def synthesize_evidence_graph(
    task: TaskSpec,
    evidence: list[EvidenceItem],
    genes: list[str],
    *,
    patterns: Iterable[StrategyPattern | dict[str, Any]] | None = None,
    paper_evidence: Iterable[dict[str, Any]] | None = None,
) -> EvidenceSynthesisResult:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    parsed_patterns = [
        pattern for pattern in (_parse_pattern(raw) for raw in (patterns or []))
        if pattern is not None
    ]
    lane_by_id = {item.evidence_id: infer_evidence_lane(item) for item in evidence}
    lane_coverage: dict[str, dict[str, list[str]]] = {}
    for item in evidence:
        gene = (item.gene_symbol or "").strip()
        lane = lane_by_id.get(item.evidence_id)
        if not gene or not lane:
            continue
        lane_coverage.setdefault(gene, {}).setdefault(lane, [])
        if item.evidence_id not in lane_coverage[gene][lane]:
            lane_coverage[gene][lane].append(item.evidence_id)
    conflict_genes, conflict_findings = _direction_conflicts(evidence, evidence_by_id)
    dependent_pairs, dependence_findings = _dependent_lane_pairs(lane_coverage, evidence_by_id)
    nodes, edges = _build_entity_graph(
        task, evidence, genes, lane_by_id, lane_coverage, evidence_by_id,
    )
    pattern_links = _build_pattern_links(
        parsed_patterns, genes, lane_coverage, evidence_by_id,
        dependent_pairs, conflict_genes,
    )
    paper_links, paper_nodes, paper_edges = _build_paper_strategy_links(
        list(paper_evidence or []), genes,
    )
    nodes.update(paper_nodes)
    edges.extend(paper_edges)
    for link in pattern_links:
        edges.append(GraphEdge(
            source=f"lane:{link['source_lane']}",
            target=f"lane:{link['target_lane']}",
            relation="pattern_evidence_link",
            evidence_ids=link["evidence_ids"],
            claim_class=ClaimClass.INFERRED,
            weight=link["weight"],
            attributes={
                "gene": link["gene"],
                "pattern_id": link["pattern_id"],
                "pattern_name": link["pattern_name"],
                "link_id": link["link_id"],
                "link_type": link["link_type"],
                "decision_rule": link["decision_rule"],
                "why_this_link": link["why_this_link"],
                "independence_note": link["independence_note"],
                "dependent": False,
            },
        ))
    lane_present = {
        lane for lanes in lane_coverage.values() for lane in lanes
    }
    multi_lane_genes = sum(1 for lanes in lane_coverage.values() if len(lanes) >= 2)
    low_context = [
        item.evidence_id for item in evidence
        if item.context_match_score < MIN_LINK_CONTEXT
    ]
    graph = CausalGraph(
        graph_kind="mechanistic_evidence",
        context=EvidenceContext(
            organism=task.context.organism, tissue=task.context.tissue,
            cell_type=task.context.cell_type, disease=task.context.disease or "disease",
            disease_stage=task.context.disease_stage,
        ),
        nodes=list(nodes.values()),
        edges=edges,
        model_statistics={
            "evidence_items": len(evidence),
            "ranked_genes": sum(1 for gene in genes if (gene or "").strip()),
            "lanes_present": sorted(lane_present),
            "genes_with_multi_lane_evidence": multi_lane_genes,
            "pattern_links": len(pattern_links),
            "paper_strategy_hints": len(paper_links),
            "conflicting_genes": sorted(conflict_genes),
            "dependent_links_withheld": len(dependence_findings),
            "low_context_excluded_from_links": len(low_context),
        },
        limitations=[
            "Edges encode evidence relations and are not automatically causal.",
            "Pattern-guided lane links are strategy hypotheses distilled from high-impact "
            "papers; they are not evidence for the current disease.",
            "Paper-RAG hits are strategy hints distilled from public abstracts; they are "
            "marked strategy_only, never enter ranking or pattern links, and are not "
            "evidence for the current disease.",
            "Edge weights are context-match multipliers for prioritization, not causal "
            "or clinical success probabilities.",
            "K562 DeltaFactor outputs with context match below 0.5 are excluded from "
            "formal ranking and pattern links.",
        ],
    )
    return EvidenceSynthesisResult(
        graph=graph,
        findings=[*conflict_findings, *dependence_findings],
        lane_coverage=lane_coverage,
        pattern_links=pattern_links,
        paper_links=paper_links,
    )


def build_mechanistic_graph(
    task: TaskSpec,
    evidence: list[EvidenceItem],
    genes: list[str],
    *,
    patterns: Iterable[StrategyPattern | dict[str, Any]] | None = None,
    paper_evidence: Iterable[dict[str, Any]] | None = None,
) -> CausalGraph:
    """Backward-compatible entry point used by the legacy and LangGraph runtimes."""
    return synthesize_evidence_graph(
        task, evidence, genes, patterns=patterns, paper_evidence=paper_evidence,
    ).graph
