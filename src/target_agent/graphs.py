"""Mechanistic evidence graph construction for disease scenarios."""
from __future__ import annotations

from .contracts import CausalGraph, ClaimClass, EvidenceContext, EvidenceItem, GraphEdge, GraphNode, TaskSpec


def build_mechanistic_graph(task: TaskSpec, evidence: list[EvidenceItem], genes: list[str]) -> CausalGraph:
    disease = task.context.disease or "disease"
    nodes: dict[str, GraphNode] = {
        "disease": GraphNode(node_id="disease", node_type="disease", label=disease),
        **{
            f"gene:{gene}": GraphNode(node_id=f"gene:{gene}", node_type="gene", label=gene)
            for gene in genes
        },
    }
    edges: list[GraphEdge] = []
    for item in evidence:
        genetic = item.genetic_evidence
        if genetic and genetic.locus_id:
            locus_id = f"locus:{genetic.study_id}:{genetic.locus_id}:{genetic.signal_id or 'unresolved'}"
            nodes.setdefault(locus_id, GraphNode(
                node_id=locus_id, node_type="locus", label=genetic.locus_id,
                attributes={
                    "study_id": genetic.study_id, "signal_id": genetic.signal_id,
                    "genome_build": item.context.genome_build, "causal_status": "not_established",
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
                    source=variant_id, target=locus_id, relation="statistical_signal_membership",
                    evidence_ids=[item.evidence_id], claim_class=ClaimClass.INFERRED,
                    weight=item.context_match_score,
                ))
            edges.append(GraphEdge(
                source=locus_id, target="disease", relation="human_genetic_association",
                evidence_ids=[item.evidence_id], claim_class=item.claim_class,
                weight=item.context_match_score,
            ))
            if item.gene_symbol in genes and genetic.formal_score_eligible:
                edges.append(GraphEdge(
                    source=locus_id, target=f"gene:{item.gene_symbol}",
                    relation="colocalization_shared_signal_hypothesis",
                    evidence_ids=[item.evidence_id], claim_class=ClaimClass.INFERRED,
                    weight=item.context_match_score,
                ))
            continue
        if item.gene_symbol not in genes:
            continue
        relation = {
            ClaimClass.FACT: "database_or_literature_association",
            ClaimClass.OBSERVED: "observed_context_association",
            ClaimClass.PREDICTED: "predicted_effect",
            ClaimClass.INFERRED: "agent_inference",
        }[item.claim_class]
        edges.append(GraphEdge(
            source=f"gene:{item.gene_symbol}", target="disease", relation=relation,
            evidence_ids=[item.evidence_id], claim_class=item.claim_class,
            weight=item.context_match_score,
        ))
    return CausalGraph(
        graph_kind="mechanistic_evidence",
        context=EvidenceContext(
            organism=task.context.organism, tissue=task.context.tissue,
            cell_type=task.context.cell_type, disease=disease, disease_stage=task.context.disease_stage,
        ),
        nodes=list(nodes.values()), edges=edges,
        limitations=[
            "Edges encode evidence relations and are not automatically causal.",
            "K562 DeltaFactor outputs with context match below 0.5 are excluded from formal ranking.",
        ],
    )
