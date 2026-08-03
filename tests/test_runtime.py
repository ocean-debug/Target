import json
import time

from target_agent.contracts import TaskContext, TaskSpec
from target_agent.planner import Planner
from target_agent.runtime import TargetDiscoveryRuntime
from target_agent.tools.base import ToolRegistry
from target_agent.tools.uc import DeltaFactorTool, ObservedTCellPerturbationTool, UCOmicsSnapshotTool

from .fakes import FakeLiterature, FakeOpenTargets


def fake_runtime(tmp_path):
    return TargetDiscoveryRuntime(
        runs_dir=tmp_path / "runs", cache_dir=tmp_path / "cache", planner=Planner(None),
        registry=ToolRegistry([
            UCOmicsSnapshotTool(), FakeOpenTargets(), FakeLiterature(),
            ObservedTCellPerturbationTool(), DeltaFactorTool(),
        ]),
    )


def uc_task():
    return TaskSpec(
        task_id="task-test-uc", task_type="disease_to_target", question="Find traceable UC targets",
        context=TaskContext(disease="ulcerative colitis", disease_id="MONDO_0005101", tissue="rectum", cell_type="T cell", desired_phenotype="restore state"),
    )


def test_cached_style_uc_three_runs_are_consistent_and_fast(tmp_path):
    runtime = fake_runtime(tmp_path)
    rankings = []
    for index in range(3):
        started = time.perf_counter()
        status = runtime.run(uc_task(), run_id=f"run-repeat-{index}")
        assert time.perf_counter() - started < 120
        assert status["terminal_status"] == "completed_with_gaps"
        run_dir = tmp_path / "runs" / f"run-repeat-{index}"
        ranking = json.loads((run_dir / "ranked_targets.json").read_text())
        cards = json.loads((run_dir / "target_cards.json").read_text())
        assert len(ranking) == 10
        assert len(cards) == 5
        assert len([row["gene"] for row in ranking[:3]]) == 3
        assert any(row["gene"] == "IL12B" for row in ranking)
        rankings.append([(row["gene"], row["scores"], row["decision"]) for row in ranking])
    assert rankings[0] == rankings[1] == rankings[2]


def test_provenance_and_deltafactor_score_boundary(tmp_path):
    runtime = fake_runtime(tmp_path)
    runtime.run(uc_task(), run_id="run-provenance")
    run_dir = tmp_path / "runs" / "run-provenance"
    tool_ids = {json.loads(line)["tool_run_id"] for line in (run_dir / "tool_results.jsonl").read_text().splitlines()}
    evidence = [json.loads(line) for line in (run_dir / "evidence_items.jsonl").read_text().splitlines()]
    assert all(item["tool_run_id"] in tool_ids and item["source_span"] for item in evidence)
    ranking = json.loads((run_dir / "ranked_targets.json").read_text())
    gpr15 = next(row for row in ranking if row["gene"] == "GPR15")
    assert gpr15["scores"]["perturbation"] == 0


def test_resume_terminal_run_is_idempotent(tmp_path):
    runtime = fake_runtime(tmp_path)
    first = runtime.run(uc_task(), run_id="run-resume")
    before = (tmp_path / "runs" / "run-resume" / "trace.jsonl").read_text()
    second = runtime.run(uc_task(), run_id="run-resume", resume=True)
    after = (tmp_path / "runs" / "run-resume" / "trace.jsonl").read_text()
    assert first == second
    assert before == after
