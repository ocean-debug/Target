"""Mechanistic evidence graph construction for disease scenarios."""
from __future__ import annotations

from .contracts import CausalGraph, ClaimClass, EvidenceContext, EvidenceItem, GraphEdge, GraphNode, TaskSpec


def build_mechanistic_graph(task: TaskSpec, evidence: list[EvidenceItem], genes: list[str]) -> CausalGraph:
    disease = task.context.disease or "disease"
    nodes = [GraphNode(node_id="disease", node_type="disease", label=disease)]
    nodes.extend(GraphNode(node_id=f"gene:{gene}", node_type="gene", label=gene) for gene in genes)
    edges = []
    for item in evidence:
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
        nodes=nodes, edges=edges,
        limitations=[
            "Edges encode evidence relations and are not automatically causal.",
            "K562 DeltaFactor outputs with context match below 0.5 are excluded from formal ranking.",
        ],
    )

