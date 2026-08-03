from __future__ import annotations

import argparse
import json
from pathlib import Path


def lines(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    tools = lines(run_dir / "tool_results.jsonl")
    evidence = lines(run_dir / "evidence_items.jsonl")
    tool_ids = {row["tool_run_id"] for row in tools}
    evidence_ids = {row["evidence_id"] for row in evidence}
    assert all(row["tool_run_id"] in tool_ids for row in evidence)
    assert all(row["source"]["uri"] and row["source_span"] for row in evidence)
    assert all(set(row["evidence_ids"]) <= evidence_ids for row in tools)
    assert all(not (row["coverage_status"] == "not_covered" and row["status"] == "success") for row in tools)
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == status["terminal_status"]
    print("RUN_CONTRACT=OK")
    print(f"TERMINAL_STATUS={status['terminal_status']}")
    print(f"TOOL_RUNS={len(tools)}")
    print(f"EVIDENCE_ITEMS={len(evidence)}")


if __name__ == "__main__":
    main()

