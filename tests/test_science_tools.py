from pathlib import Path

from target_agent.contracts import TaskContext, TaskSpec
from target_agent.tools.base import ToolContext
from target_agent.tools.literature import stable_chunks
from target_agent.tools.mch import MCHCausalGoldTool
from target_agent.tools.uc import DeltaFactorTool, ObservedTCellPerturbationTool, UCOmicsSnapshotTool


def ctx(tmp_path: Path, disease="ulcerative colitis", trait=None, genes=None):
    task_type = "trait_mechanism" if trait else "disease_to_target"
    return ToolContext(
        task=TaskSpec(
            task_type=task_type, question="test task",
            context=TaskContext(disease=None if trait else disease, desired_phenotype=trait, tissue="rectum", cell_type="T cell"),
        ),
        run_dir=tmp_path / "run", cache_dir=tmp_path / "cache", candidate_genes=genes or ["IL2", "CD27", "GPR15"],
    )


def test_uc_success_and_crohn_out_of_scope(tmp_path):
    ok = UCOmicsSnapshotTool().run(ctx(tmp_path))
    assert ok.result.status.value == "success"
    assert len(ok.result.outputs["candidates"]) == 20
    assert all(item.tool_run_id == ok.result.tool_run_id for item in ok.evidence)
    ood = UCOmicsSnapshotTool().run(ctx(tmp_path, disease="Crohn disease"))
    assert ood.result.status.value == "out_of_scope"
    assert ood.result.coverage_status.value == "not_covered"


def test_observed_perturbation_is_partial_and_honest(tmp_path):
    result = ObservedTCellPerturbationTool().run(ctx(tmp_path))
    assert result.result.status.value == "partial"
    assert set(result.result.outputs["uncovered_genes"]) == {"GPR15"}
    assert all(item.claim_class.value == "OBSERVED" for item in result.evidence)
    assert all("activation_not_inhibition" in item.quality_flags for item in result.evidence)


def test_deltafactor_uc_is_excluded(tmp_path):
    result = DeltaFactorTool().run(ctx(tmp_path))
    assert result.result.context_match_score < 0.5
    assert result.result.outputs["formal_score_eligible"] is False
    assert result.evidence == []


def test_mch_metrics_separated_and_non_mch_refused(tmp_path):
    mch = MCHCausalGoldTool().run(ctx(tmp_path, trait="MCH"))
    assert mch.result.outputs["paper_result"]["direction_prediction"] == {"correct": 43, "total": 59, "accuracy": 0.7288135593}
    assert mch.result.outputs["project_replication"]["direction_prediction"]["correct"] == 94
    non_mch = MCHCausalGoldTool().run(ctx(tmp_path, trait="LDL"))
    assert non_mch.result.status.value == "out_of_scope"
    assert non_mch.result.outputs["graph"] is None


def test_stable_chunk_ids_and_literal_text():
    a = stable_chunks("PMID1", "A " * 1000)
    b = stable_chunks("PMID1", "A " * 1000)
    assert [x["chunk_id"] for x in a] == [x["chunk_id"] for x in b]
    assert all(x["text"] for x in a)

