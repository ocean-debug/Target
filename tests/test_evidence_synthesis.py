"""Deterministic evidence-synthesis and mechanism-graph quality gates."""
from __future__ import annotations

from target_agent.contracts import (
    ClaimClass, EvidenceContext, EvidenceItem, GeneticEvidencePayload,
    SourceLocator, Stance, TaskContext, TaskSpec,
)
from target_agent.graphs import (
    build_mechanistic_graph, infer_evidence_lane, synthesize_evidence_graph,
)
from target_agent.paper_strategy import EvidenceLink, SourcePaper, StrategyPattern


def _evidence(
    gene: str,
    *,
    lane: str = "literature",
    context_match: float = 0.9,
    effect: dict | None = None,
    context: dict | None = None,
    genetic: GeneticEvidencePayload | None = None,
    tool_run: str = "tool-a",
    source_id: str = "source-a",
    direction: str = "unclear",
    claim_class: ClaimClass = ClaimClass.FACT,
    section: str | None = None,
) -> EvidenceItem:
    ctx_values: dict = {
        "disease": "test disease", "tissue": "lung", "cell_type": "T cell",
    }
    if context:
        ctx_values.update(context)
    if lane == "perturbation":
        ctx_values["perturbation_type"] = "CRISPRa"
    if genetic is not None:
        ctx_values.update({
            "study_id": genetic.study_id, "locus_id": genetic.locus_id,
            "signal_id": genetic.signal_id, "genome_build": "GRCh38",
            "ancestry": "EUR",
        })
    if effect is None:
        if lane == "omics":
            effect = {"log2fc": 1.2, "fdr": 0.01, "accession": "GSE1"}
        elif lane == "drug":
            effect = {"drug": {"drugId": "CHEMBL-1", "prefName": "TestDrug", "phase": 2}}
        elif lane == "safety":
            effect = {"safety": {"event": "QT prolongation"}}
        else:
            effect = {}
    values: dict = {
        "tool_run_id": tool_run,
        "gene_symbol": gene,
        "claim_class": claim_class,
        "statement": f"test evidence for {gene} in lane {lane}",
        "source": SourceLocator(uri="https://example.org/test", source_id=source_id, section=section),
        "source_span": f"gene={gene}",
        "context": EvidenceContext(**ctx_values),
        "stance": Stance.SUPPORTS,
        "effect_direction": direction,
        "effect": effect,
        "uncertainty": "test fixture",
        "context_match_score": context_match,
    }
    if genetic is not None:
        values["genetic_evidence"] = genetic
    return EvidenceItem(**values)


def _genetic(gene: str, *, formal: bool = True) -> GeneticEvidencePayload:
    if formal:
        return GeneticEvidencePayload(
            evidence_type="locus_to_gene",
            analysis_level="colocalization_supported",
            study_id="GWAS-1", molecular_study_id="EQTL-1", locus_id="locus-1",
            variant_id="chr1:100", signal_id="signal-1", gene_symbol=gene,
            method="coloc", method_version="5.1", strength=0.9,
            formal_score_eligible=True,
        )
    return GeneticEvidencePayload(
        evidence_type="gwas_association",
        analysis_level="association_only",
        study_id="GWAS-1", locus_id="locus-1", variant_id="chr1:100",
        gene_symbol=None, strength=0.0, formal_score_eligible=False,
    )


def _task() -> TaskSpec:
    return TaskSpec(
        task_type="disease_to_target",
        question="test",
        context=TaskContext(disease="test disease", tissue="lung", cell_type="T cell"),
    )


def _pattern(lanes: tuple[str, str]) -> StrategyPattern:
    return StrategyPattern(
        pattern_id="pattern-test",
        name="Test pattern",
        disease_class="autoimmune",
        applicability=["test disease"],
        evidence_start_lane=lanes[0],
        ordered_lanes=list(lanes),
        required_lanes=[lanes[0]],
        evidence_links=[
            EvidenceLink(
                link_id="link-1", source_lane=lanes[0], target_lane=lanes[1],
                link_type="cross_layer_support", evidence_used=[],
                decision_rule="both lanes must support the same gene",
                why_this_link="recent papers connect these layers",
            )
        ],
        stop_downgrade_rules=["no independent support means no link"],
        mixed_method_rationale="different layers resolve different hypotheses",
        source_papers=[SourcePaper(title="Test paper", journal="Nature", year=2025)],
    )


def test_lane_inference_reads_structured_fields():
    items = [
        _evidence("G1", lane="genetics", genetic=_genetic("G1")),
        _evidence("G1", lane="omics"),
        _evidence("G1", lane="perturbation"),
        _evidence("G1", lane="drug"),
        _evidence("G1", lane="safety"),
        _evidence("G1", lane="literature"),
    ]
    assert [infer_evidence_lane(item) for item in items] == [
        "genetics", "omics", "perturbation", "drug", "safety", "literature",
    ]


def test_graph_contains_entities_lanes_and_safety_blocker():
    genetic = _genetic("G1")
    evidence = [
        _evidence("G1", lane="genetics", genetic=genetic),
        _evidence("G1", lane="omics", context={"tissue": "colon"}),
        _evidence("G1", lane="drug"),
        _evidence("G2", lane="safety"),
    ]
    result = synthesize_evidence_graph(_task(), evidence, ["G1", "G2"])
    graph = result.graph
    node_types = {node.node_type for node in graph.nodes}
    assert {"disease", "gene", "locus", "cell_state", "drug", "lane"} <= node_types
    relations = {edge.relation for edge in graph.edges}
    assert {"colocalization_shared_signal_hypothesis", "context_localization",
            "known_drug_link", "has_evidence_in", "evidence_lane_supports_disease",
            "safety_liability"} <= relations
    safety = [edge for edge in graph.edges if edge.relation == "safety_liability"]
    assert safety and safety[0].attributes["safety_blocker"] is True
    assert graph.model_statistics["lanes_present"] == ["drug", "genetics", "omics", "safety"]


def test_pattern_link_created_when_two_independent_lanes_covered():
    evidence = [
        _evidence("G1", lane="genetics", genetic=_genetic("G1"), tool_run="tool-gen"),
        _evidence("G1", lane="omics", tool_run="tool-omics"),
    ]
    result = synthesize_evidence_graph(_task(), evidence, ["G1"], patterns=[_pattern(("genetics", "omics"))])
    assert len(result.pattern_links) == 1
    link = result.pattern_links[0]
    assert link["gene"] == "G1" and link["source_lane"] == "genetics" and link["target_lane"] == "omics"
    assert link["weight"] == 0.9
    pattern_edges = [edge for edge in result.graph.edges if edge.relation == "pattern_evidence_link"]
    assert len(pattern_edges) == 1
    assert pattern_edges[0].claim_class == ClaimClass.INFERRED
    assert pattern_edges[0].attributes["pattern_id"] == "pattern-test"


def test_pattern_link_withheld_on_direction_conflict():
    evidence = [
        _evidence("G1", lane="genetics", genetic=_genetic("G1"), tool_run="tool-gen"),
        _evidence("G1", lane="omics", direction="increase", context={"tissue": "lung"}, tool_run="tool-o1"),
        _evidence("G1", lane="omics", direction="decrease", context={"tissue": "lung"}, tool_run="tool-o2"),
    ]
    result = synthesize_evidence_graph(_task(), evidence, ["G1"], patterns=[_pattern(("genetics", "omics"))])
    assert result.pattern_links == []
    assert any(row["category"] == "conflicting_evidence" and row["severity"] == "blocking"
               for row in result.findings)
    assert result.graph.model_statistics["conflicting_genes"] == ["G1"]


def test_pattern_link_withheld_when_lanes_share_lineage():
    evidence = [
        _evidence("G1", lane="genetics", genetic=_genetic("G1"), tool_run="tool-ot", source_id="ot:1"),
        _evidence("G1", lane="drug", tool_run="tool-ot", source_id="ot:1"),
    ]
    result = synthesize_evidence_graph(_task(), evidence, ["G1"], patterns=[_pattern(("genetics", "drug"))])
    assert result.pattern_links == []
    assert any(row["category"] == "evidence_dependence" for row in result.findings)
    assert result.graph.model_statistics["dependent_links_withheld"] == 1


def test_low_context_evidence_excluded_from_pattern_links():
    evidence = [
        _evidence("G1", lane="genetics", genetic=_genetic("G1"), context_match=0.9, tool_run="tool-gen"),
        _evidence("G1", lane="omics", context_match=0.4, tool_run="tool-omics"),
    ]
    result = synthesize_evidence_graph(_task(), evidence, ["G1"], patterns=[_pattern(("genetics", "omics"))])
    assert result.pattern_links == []
    assert result.graph.model_statistics["low_context_excluded_from_links"] == 1


def test_build_mechanistic_graph_keeps_backward_compatible_signature():
    evidence = [
        _evidence("G1", lane="genetics", genetic=_genetic("G1")),
        _evidence("G1", lane="omics"),
    ]
    graph = build_mechanistic_graph(_task(), evidence, ["G1"])
    assert graph.graph_kind == "mechanistic_evidence"
    assert any(edge.relation == "has_evidence_in" for edge in graph.edges)


def _paper_evidence(gene: str, chunk_id: str = "chunk-0-paper-0", pmid: str = "12345678") -> list[dict]:
    return [{
        "kind": "paper_rag",
        "chunk_id": chunk_id,
        "pmid": pmid,
        "title": f"{gene} mechanism in test disease",
        "journal": "Nature",
        "year": 2025,
        "lane_tags": ["genetics", "omics"],
        "snippet": f"{gene} regulates test disease",
        "score": 4.0,
        "strategy_hint_not_evidence": True,
    }]


def test_paper_rag_hits_projected_as_strategy_only_nodes():
    evidence = [_evidence("G1", lane="genetics", genetic=_genetic("G1"))]
    synthesis = synthesize_evidence_graph(
        _task(), evidence, ["G1"], paper_evidence=_paper_evidence("G1"),
    )
    node_ids = {node.node_id for node in synthesis.graph.nodes}
    assert "strategy:paper:chunk-0-paper-0" in node_ids
    hint_edges = [
        edge for edge in synthesis.graph.edges
        if edge.relation == "paper_strategy_hint"
    ]
    assert len(hint_edges) == 1
    edge = hint_edges[0]
    assert edge.claim_class == ClaimClass.INFERRED
    assert edge.weight == 0.0
    assert edge.attributes["strategy_only"] is True
    assert edge.attributes["not_evidence"] is True
    assert edge.evidence_ids == []
    assert synthesis.paper_links and synthesis.paper_links[0]["gene"] == "G1"
    assert synthesis.paper_links[0]["strategy_hint_not_evidence"] is True
    assert synthesis.graph.model_statistics["paper_strategy_hints"] == 1


def test_paper_rag_hits_never_change_lane_coverage_or_pattern_links():
    evidence = [_evidence("G1", lane="genetics", genetic=_genetic("G1"))]
    baseline = synthesize_evidence_graph(_task(), evidence, ["G1"])
    with_hits = synthesize_evidence_graph(
        _task(), evidence, ["G1"], paper_evidence=_paper_evidence("G1"),
    )
    assert with_hits.lane_coverage == baseline.lane_coverage
    assert with_hits.pattern_links == baseline.pattern_links
    assert with_hits.findings == baseline.findings


def test_paper_rag_hits_for_unknown_genes_and_malformed_rows_are_skipped():
    evidence = [_evidence("G1", lane="literature")]
    synthesis = synthesize_evidence_graph(
        _task(), evidence, ["G1"],
        paper_evidence=[
            {
                "chunk_id": "chunk-0-paper-0",
                "pmid": "1",
                "title": "NO_GENE_HERE mentions nothing",
                "snippet": "x",
            },
            {"pmid": "2"},
            None,
            _paper_evidence("UNKNOWN_GENE")[0],
        ],
    )
    assert synthesis.graph.model_statistics["paper_strategy_hints"] == 0
    assert synthesis.paper_links == []
    assert not any(
        edge.relation == "paper_strategy_hint" for edge in synthesis.graph.edges
    )


def test_build_mechanistic_graph_accepts_paper_evidence_parameter():
    evidence = [_evidence("G1", lane="omics")]
    graph = build_mechanistic_graph(
        _task(), evidence, ["G1"], paper_evidence=_paper_evidence("G1"),
    )
    assert graph.model_statistics["paper_strategy_hints"] == 1
    assert any(
        edge.relation == "paper_strategy_hint" for edge in graph.edges
    )
