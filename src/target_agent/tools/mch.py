"""MCH-only causal-modelling gold sample; refuses every other trait."""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..contracts import (
    ArtifactRef, CausalGraph, ClaimClass, CoverageStatus, EvidenceContext,
    EvidenceItem, GraphEdge, GraphNode, SourceLocator, Stance, ToolCapability,
    ToolResult, ToolStatus, new_id,
)
from .base import ScientificTool, ToolContext, ToolExecution


ROOT = Path(__file__).resolve().parents[3]
NATURE_URI = "https://www.nature.com/articles/s41586-025-09866-3"


class MCHCausalGoldTool(ScientificTool):
    name = "mch_causal_gold"
    version = "2.0.0"

    def run(self, context: ToolContext) -> ToolExecution:
        started = time.perf_counter()
        run_id = new_id("tool")
        trait = (context.task.context.desired_phenotype or "").strip().upper()
        capability = ToolCapability(
            supported_organisms=["Homo sapiens"], supported_tissues=["K562 cell line", "human blood trait genetics"],
            supported_cell_types=["K562"], supported_perturbations=["Perturb-seq"],
            training_scope="K562 regulator-to-program perturbation effects",
            validation_scope="Mean corpuscular haemoglobin (MCH) only",
        )
        if trait != "MCH":
            return ToolExecution(result=ToolResult(
                tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
                status=ToolStatus.OUT_OF_SCOPE, coverage_status=CoverageStatus.NOT_COVERED, context_match_score=0.0,
                inputs={"trait": trait}, outputs={"covered": False, "graph": None}, capability=capability,
                warnings=["trait_out_of_scope"],
                limitations=["The cached causal model is valid only for the exact MCH configuration; no fixed graph is emitted for another trait."],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            ), evidence=[])
        payload = json.loads((ROOT / "data" / "derived" / "mch_gold_v2.json").read_text(encoding="utf-8"))
        paper = payload["paper"]
        replication = payload["project_replication"]
        evidence = [
            EvidenceItem(
                tool_run_id=run_id, gene_symbol=None, claim_class=ClaimClass.FACT,
                statement="The paper reports 43 of 59 MCH perturbation-effect directions predicted correctly.",
                source=SourceLocator(uri=NATURE_URI, source_id="s41586-025-09866-3", version="2025", section="MCH direction prediction", chunk_id="paper-mch-43-59"),
                source_span="MCH paper configuration: correct=43|total=59|accuracy=0.7288135593",
                context=EvidenceContext(organism="Homo sapiens", tissue="K562 and blood-trait genetics", cell_type="K562", assay=paper["method"]),
                stance=Stance.SUPPORTS, effect=paper["direction_prediction"],
                uncertainty="This metric applies to the paper's 59-hit MCH configuration only.",
                quality_flags=["paper_reported_metric"], context_match_score=1.0,
            ),
            EvidenceItem(
                tool_run_id=run_id, gene_symbol=None, claim_class=ClaimClass.OBSERVED,
                statement="The project's expanded MCH reproduction predicted 94 of 147 directions correctly (permutation P=0.00019998).",
                source=SourceLocator(uri="artifact://data/derived/mch_gold_v2.json", source_id="mch_sign_prediction.csv", version="v2-snapshot", section="project_replication", chunk_id="project-mch-94-147"),
                source_span="extended project configuration: correct=94|total=147|accuracy=0.6394557823|permutation_p=0.0001999800",
                context=EvidenceContext(organism="Homo sapiens", tissue="K562 and blood-trait genetics", cell_type="K562", assay="extended reproduction"),
                stance=Stance.SUPPORTS, effect=replication["direction_prediction"],
                uncertainty="The hit set differs from the paper and must not be labelled a reproduction of the paper's 73% accuracy.",
                quality_flags=["different_hit_set_from_paper"], context_match_score=1.0,
            ),
            EvidenceItem(
                tool_run_id=run_id, gene_symbol="HBA1", claim_class=ClaimClass.OBSERVED,
                statement=(f"The project Fig.3a regression gave beta={replication['fig3a']['beta']:.6g} and "
                           f"P={replication['fig3a']['p_value']:.3g}, close to the paper beta=0.052 and P=3e-7."),
                source=SourceLocator(uri="artifact://data/derived/mch_gold_v2.json", source_id="fig3a_summary.json", version="v2-snapshot", section="fig3a", chunk_id="project-fig3a-hba1"),
                source_span=(f"HBA1|n={replication['fig3a']['n_perturbed_genes']}|beta={replication['fig3a']['beta']}|"
                             f"p={replication['fig3a']['p_value']}|paper_beta={paper['fig3a']['beta']}|paper_p={paper['fig3a']['p_value']}"),
                context=EvidenceContext(organism="Homo sapiens", tissue="K562 and blood-trait genetics", cell_type="K562", assay="sHet-adjusted regression"),
                stance=Stance.SUPPORTS, effect={"project": replication["fig3a"], "paper": paper["fig3a"]},
                uncertainty="Numerical agreement validates this configured regression, not transfer to another trait or tissue.",
                quality_flags=["configuration_specific"], context_match_score=1.0,
            ),
        ]
        nodes = [GraphNode(node_id="MCH", node_type="trait", label="Mean corpuscular haemoglobin")]
        nodes.extend(GraphNode(node_id=p["id"], node_type="program", label=p["label"]) for p in payload["graph"]["programs"])
        nodes.extend(GraphNode(node_id=g, node_type="gene", label=g) for g in payload["graph"]["regulators"])
        edges = [
            GraphEdge(source=program["id"], target="MCH", relation="program_to_trait", evidence_ids=[evidence[0].evidence_id, evidence[1].evidence_id], claim_class=ClaimClass.OBSERVED)
            for program in payload["graph"]["programs"]
        ]
        graph = CausalGraph(
            graph_kind="causal_model",
            context=EvidenceContext(organism="Homo sapiens", tissue="K562 and blood-trait genetics", cell_type="K562", assay=paper["method"]),
            nodes=nodes, edges=edges,
            model_statistics={"paper": paper["direction_prediction"], "project_replication": replication},
            source_artifacts=[ArtifactRef(name="mch_gold_v2.json", uri="artifact://data/derived/mch_gold_v2.json", media_type="application/json")],
            limitations=payload["limitations"],
        )
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED, context_match_score=1.0,
            inputs={"trait": trait}, outputs={"covered": True, "paper_result": paper, "project_replication": replication, "graph": graph.model_dump(mode="json")},
            capability=capability, data_version="mch_gold:v2", code_version="2.0.0",
            parameters={"paper_configuration": "59 hits", "extended_configuration": "147 hits", "permutations": 10000},
            evidence_ids=[item.evidence_id for item in evidence], limitations=payload["limitations"], cached=True,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return ToolExecution(result=result, evidence=evidence)

