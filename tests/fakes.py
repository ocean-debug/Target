from __future__ import annotations

from target_agent.contracts import (
    ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, SourceLocator,
    Stance, ToolCapability, ToolResult, ToolStatus, new_id,
)
from target_agent.tools.base import ScientificTool, ToolContext, ToolExecution


class FakeOpenTargets(ScientificTool):
    name = "open_targets"
    version = "test"

    def run(self, context: ToolContext) -> ToolExecution:
        run_id = new_id("tool")
        rows = []
        evidence = []
        for gene, score, drug in [("IL2", 0.8, "TestDrug-A"), ("CD27", 0.65, "TestDrug-B"), ("IL12B", 0.9, "TestDrug-C")]:
            if gene not in context.candidate_genes and gene != "IL12B":
                continue
            drug_row = {"targetId": f"ENSG-{gene}", "drugId": f"CHEMBL-{gene}", "prefName": drug, "phase": 2, "status": "test fixture"}
            rows.append({"gene": gene, "target_id": f"ENSG-{gene}", "association_score": score, "genetic_score": score, "datatype_scores": {"genetic_association": score}, "known_drugs": [drug_row]})
            evidence.append(EvidenceItem(
                tool_run_id=run_id, gene_symbol=gene, claim_class=ClaimClass.FACT,
                statement=f"Fixture Open Targets genetic score for {gene} is {score}.",
                source=SourceLocator(uri="https://platform.opentargets.org/test", source_id=f"fixture-{gene}", chunk_id=f"fixture-ot-{gene}"),
                source_span=f"gene={gene}|genetic_score={score}",
                context=EvidenceContext(organism="Homo sapiens", disease="ulcerative colitis", assay="fixture"),
                stance=Stance.SUPPORTS, effect={"genetic_score": score},
                uncertainty="Synthetic test fixture, never used as demo evidence.", quality_flags=["test_fixture"], context_match_score=1.0,
            ))
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED, context_match_score=1.0,
            inputs={}, outputs={"covered": True, "associations": rows,
                                "top_genetic_candidates": [{"gene": "IL12B", "target_id": "ENSG-IL12B", "genetic_score": 0.9}]},
            capability=ToolCapability(validation_scope="test fixture"), evidence_ids=[item.evidence_id for item in evidence],
        )
        return ToolExecution(result=result, evidence=evidence)


class FakeLiterature(ScientificTool):
    name = "europe_pmc_rag"
    version = "test"

    def run(self, context: ToolContext) -> ToolExecution:
        run_id = new_id("tool")
        evidence = []
        if "IL2" in context.candidate_genes:
            quote = "IL2 was explicitly evaluated in an ulcerative colitis test fixture."
            evidence.append(EvidenceItem(
                tool_run_id=run_id, gene_symbol="IL2", claim_class=ClaimClass.FACT,
                statement="The fixture source explicitly co-mentions IL2 and ulcerative colitis.",
                source=SourceLocator(uri="https://europepmc.org/test", source_id="fixture-pmid", chunk_id="fixture-lit-il2"),
                source_span=quote, context=EvidenceContext(disease="ulcerative colitis", assay="fixture"),
                stance=Stance.SUPPORTS, uncertainty="Synthetic test fixture, never used as demo evidence.",
                quality_flags=["test_fixture"], context_match_score=1.0,
            ))
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS, coverage_status=CoverageStatus.COVERED, context_match_score=1.0,
            inputs={}, outputs={"search_hits": 1, "extracted_claims": len(evidence), "search_hits_are_evidence": False},
            capability=ToolCapability(validation_scope="test fixture"), evidence_ids=[item.evidence_id for item in evidence],
        )
        return ToolExecution(result=result, evidence=evidence)
