from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "data" / "derived" / "mch_gold_v2.json").read_text(encoding="utf-8"))
    paper = payload["paper"]
    project = payload["project_replication"]
    assert paper["direction_prediction"]["correct"] == 43
    assert paper["direction_prediction"]["total"] == 59
    assert project["direction_prediction"]["correct"] == 94
    assert project["direction_prediction"]["total"] == 147
    assert abs(project["fig3a"]["beta"] - paper["fig3a"]["beta"]) < 0.001
    assert abs(project["fig3a"]["p_value"] - paper["fig3a"]["p_value"]) < 1e-7
    assert project["direction_prediction"]["permutation_p"] < 0.001
    print("MCH_GOLD_BOUNDARY=OK")
    print("PAPER_DIRECTION=43/59")
    print("PROJECT_EXTENSION=94/147")
    print("FIG3A_NUMERIC_CHECK=OK")


if __name__ == "__main__":
    main()

