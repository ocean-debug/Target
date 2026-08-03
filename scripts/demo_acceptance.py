from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import yaml

from target_agent.contracts import TaskSpec
from target_agent.runtime import TargetDiscoveryRuntime


def load(path: Path) -> TaskSpec:
    return TaskSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def run_timed(runtime: TargetDiscoveryRuntime, task: TaskSpec, run_id: str) -> tuple[dict, float]:
    started = time.perf_counter()
    status = runtime.run(task, run_id=run_id)
    return status, time.perf_counter() - started


def ranking(run_dir: Path) -> list[tuple]:
    rows = json.loads((run_dir / "ranked_targets.json").read_text(encoding="utf-8"))
    return [(row["gene"], row["scores"], row["decision"]) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="acceptance")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    runs = root / "runs"
    cache = root / "cache"
    runtime = TargetDiscoveryRuntime(runs_dir=runs, cache_dir=cache)
    uc = load(root / "cases" / "main_demo" / "input.uc_demo.yaml")
    mch = load(root / "cases" / "main_demo" / "input.mch_gold.yaml")
    crohn = load(root / "cases" / "main_demo" / "input.ood_crohn.yaml")

    os.environ.pop("TARGET_AGENT_CACHE_ONLY", None)
    prime_id = f"run-{args.prefix}-prime"
    prime_status, prime_seconds = run_timed(runtime, uc, prime_id)

    os.environ["TARGET_AGENT_CACHE_ONLY"] = "1"
    repeated = []
    reference = None
    for index in range(1, 4):
        run_id = f"run-{args.prefix}-cache-{index}"
        status, seconds = run_timed(runtime, uc, run_id)
        assert seconds < 120, f"cached UC run exceeded two minutes: {seconds}"
        current = ranking(runs / run_id)
        reference = current if reference is None else reference
        assert current == reference, "cached UC scientific ranking changed across repetitions"
        report = json.loads((runs / run_id / "report.json").read_text(encoding="utf-8"))
        assert len(report["ranked_targets"]) == 10
        assert len(report["target_cards"]) == 5
        assert len(report["highlighted_targets"]) == 3
        repeated.append({"run_id": run_id, "seconds": seconds, "status": status["terminal_status"]})

    mch_status, mch_seconds = run_timed(runtime, mch, f"run-{args.prefix}-mch")
    crohn_status, crohn_seconds = run_timed(runtime, crohn, f"run-{args.prefix}-crohn")
    assert mch_status["terminal_status"] == "completed"
    assert crohn_status["terminal_status"] == "needs_input"

    summary = {
        "prime": {"run_id": prime_id, "seconds": prime_seconds, "status": prime_status["terminal_status"]},
        "cached_repetitions": repeated,
        "cached_scientific_conclusion_consistent": True,
        "mch": {"seconds": mch_seconds, "status": mch_status["terminal_status"]},
        "crohn_ood": {"seconds": crohn_seconds, "status": crohn_status["terminal_status"]},
    }
    output = root / "artifacts" / f"{args.prefix}-demo-acceptance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("REAL_DEMO_ACCEPTANCE=OK")


if __name__ == "__main__":
    main()

