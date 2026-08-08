import json
import time

from target_agent.contracts import TaskContext, TaskSpec
from target_agent.planner import Planner
from target_agent.runtime import TargetDiscoveryRuntime
from target_agent.store import EvidenceStore
from target_agent.tools.base import ToolRegistry

from .fakes import FakeGenericOmics, FakeLiterature, FakeOpenTargets


def fake_runtime(tmp_path):
    return TargetDiscoveryRuntime(
        runs_dir=tmp_path / "runs", cache_dir=tmp_path / "cache", planner=Planner(None),
        registry=ToolRegistry([
            FakeGenericOmics(), FakeOpenTargets(), FakeLiterature(),
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
        assert status["terminal_status"] == "completed"
        run_dir = tmp_path / "runs" / f"run-repeat-{index}"
        ranking = json.loads((run_dir / "ranked_targets.json").read_text())
        cards = json.loads((run_dir / "target_cards.json").read_text())
        assert len(ranking) == 10
        assert len(cards) == 5
        assert len([row["gene"] for row in ranking[:3]]) == 3
        assert all(row["scores"]["human_genetics"] == 0 for row in ranking)
        rankings.append([(row["gene"], row["scores"], row["decision"]) for row in ranking])
    assert rankings[0] == rankings[1] == rankings[2]


def test_provenance_and_missing_perturbation_score_boundary(tmp_path):
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


def test_resume_uses_stored_task_identity_for_unfinished_run(tmp_path):
    runtime = fake_runtime(tmp_path)
    original = TaskSpec(
        task_type="disease_to_target", question="Find traceable UC targets",
        context=TaskContext(
            disease="ulcerative colitis", disease_id="MONDO_0005101",
            tissue="rectum", cell_type="T cell", desired_phenotype="restore state",
        ),
    )
    run_dir = tmp_path / "runs" / "run-unfinished"
    store = EvidenceStore(run_dir)
    store.save_task(original)
    store.checkpoint({"stage": "intake", "completed_steps": [], "candidate_genes": [], "tool_calls": 0})

    reloaded_input = TaskSpec(
        task_type="disease_to_target", question="Find traceable UC targets",
        context=TaskContext(
            disease="ulcerative colitis", disease_id="MONDO_0005101",
            tissue="rectum", cell_type="T cell", desired_phenotype="restore state",
        ),
    )
    assert reloaded_input.task_id != original.task_id
    status = runtime.run(reloaded_input, run_id="run-unfinished", resume=True)

    saved_task = json.loads((run_dir / "task_spec.json").read_text())
    plan = json.loads((run_dir / "execution_plan.json").read_text())
    assert status["task_id"] == original.task_id
    assert saved_task["task_id"] == original.task_id
    assert plan["task_id"] == original.task_id


def test_store_loads_homogeneous_2_1_task_through_explicit_adapter(tmp_path):
    run_dir = tmp_path / "runs" / "run-v21"
    run_dir.mkdir(parents=True)
    (run_dir / "task_spec.json").write_text(json.dumps({
        "contract_version": "2.1.0",
        "task_id": "task-v21",
        "task_type": "disease_to_target",
        "question": "Find traceable UC targets",
        "context": {
            "contract_version": "2.1.0",
            "disease": "ulcerative colitis",
        },
        "constraints": {"contract_version": "2.1.0"},
    }), encoding="utf-8")

    task = EvidenceStore(run_dir).load_task()

    assert task is not None
    assert task.contract_version == "2.2.0"
    assert task.task_id == "task-v21"
