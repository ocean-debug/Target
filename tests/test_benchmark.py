"""Fast smoke test for the benchmark runner wiring (full suite: python benchmark/runner.py)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))

from runner import check_assertion, observable, public_path_label, run_task  # noqa: E402


def goldset_entry(task_id):
    for line in (ROOT / "benchmark" / "goldset_v2.jsonl").read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry["id"] == task_id:
            return entry
    raise AssertionError(f"{task_id} missing from goldset")


def test_benchmark_refusal_task_passes(tmp_path):
    report = run_task(goldset_entry("BM-08"), tmp_path)
    assert report["passed"], [a["failure"] for a in report["results"] if not a["passed"]]


def test_non_unit_benchmark_tasks_declare_current_contract():
    entries = [
        json.loads(line)
        for line in (ROOT / "benchmark" / "goldset_v2.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert all(
        entry["task"]["contract_version"] == "2.2.0"
        for entry in entries
        if entry["mode"] != "unit"
    )


def test_benchmark_report_path_labels_do_not_expose_absolute_paths(tmp_path):
    assert public_path_label(ROOT / "benchmark" / "goldset_v2.jsonl") == \
        "benchmark/goldset_v2.jsonl"
    assert public_path_label(tmp_path / "private" / "goldset.jsonl") == "goldset.jsonl"


def test_benchmark_unit_tasks_pass(tmp_path):
    for task_id in ("BM-09", "BM-10", "BM-11"):
        report = run_task(goldset_entry(task_id), tmp_path)
        assert report["passed"], [a["failure"] for a in report["results"] if not a["passed"]]


def test_benchmark_observable_and_category_assertion_read_authoritative_reviewer_ledger(tmp_path):
    (tmp_path / "status.json").write_text('{"terminal_status":"completed_with_gaps"}\n')
    (tmp_path / "reviewer_findings.jsonl").write_text(
        '{"category":"conflicting_evidence","severity":"major","message":"opposing directions"}\n'
    )
    (tmp_path / "evidence_items.jsonl").write_text("")
    (tmp_path / "trace.jsonl").write_text("")
    (tmp_path / "tool_results.jsonl").write_text("")

    view = observable(tmp_path)

    assert view["findings"] == [("conflicting_evidence", "major")]
    assert check_assertion(
        {"type": "finding_category", "category": "conflicting_evidence"},
        {"run_dir": tmp_path},
    ) is None
