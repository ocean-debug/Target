"""Fast smoke test for the benchmark runner wiring (full suite: python benchmark/runner.py)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))

from runner import run_task  # noqa: E402


def goldset_entry(task_id):
    for line in (ROOT / "benchmark" / "goldset_v2.jsonl").read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry["id"] == task_id:
            return entry
    raise AssertionError(f"{task_id} missing from goldset")


def test_benchmark_refusal_task_passes(tmp_path):
    report = run_task(goldset_entry("BM-08"), tmp_path)
    assert report["passed"], [a["failure"] for a in report["results"] if not a["passed"]]


def test_benchmark_unit_tasks_pass(tmp_path):
    for task_id in ("BM-09", "BM-10", "BM-11"):
        report = run_task(goldset_entry(task_id), tmp_path)
        assert report["passed"], [a["failure"] for a in report["results"] if not a["passed"]]
