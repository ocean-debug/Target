import json

import pytest

from target_agent.alignment import generate, load_reviewed_rows


def test_alignment_factory_counts_and_review_gate(tmp_path):
    counts = generate(tmp_path)
    assert counts == {"sft": 120, "preferences": 60, "heldout": 30}
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["automated_training_allowed"] is False
    with pytest.raises(ValueError, match="dual approval"):
        load_reviewed_rows(tmp_path / "reviewer_sft.jsonl", allow_pending=False)

