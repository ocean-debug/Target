"""Disease-library benchmark goldset: generator determinism, entry validity,
expectation->assertion mapping, and the new causal/finding assertions."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))
sys.path.insert(0, str(ROOT / "src"))

import generate_disease_goldset as gen  # noqa: E402
from runner import check_assertion, run_task  # noqa: E402
from target_agent.contracts import TaskSpec  # noqa: E402
from target_agent.diseases import TEMPLATE_KINDS  # noqa: E402


def load_entries(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_generator_is_deterministic():
    assert gen.render(gen.build_entries(live=False)) == gen.render(gen.build_entries(live=False))
    assert gen.render(gen.build_entries(live=True)) == gen.render(gen.build_entries(live=True))


def test_committed_goldsets_are_up_to_date():
    assert (ROOT / "benchmark" / "goldset_diseases.jsonl").read_text(encoding="utf-8") == \
        gen.render(gen.build_entries(live=False))
    assert (ROOT / "benchmark" / "goldset_diseases_lora.jsonl").read_text(encoding="utf-8") == \
        gen.render(gen.build_entries(live=True))


def test_generated_entries_cover_library_and_validate():
    entries = load_entries(ROOT / "benchmark" / "goldset_diseases.jsonl")
    live_entries = load_entries(ROOT / "benchmark" / "goldset_diseases_lora.jsonl")
    assert len(entries) == len(live_entries) == 72  # 18 diseases x 4 buckets
    for collection in (entries, live_entries):
        ids = [e["id"] for e in collection]
        assert len(ids) == len(set(ids))
        buckets = {e["category"].removeprefix("disease_library_") for e in collection}
        assert buckets == set(TEMPLATE_KINDS)
        for entry in collection:
            TaskSpec.model_validate(entry["task"])  # every embedded task is contract-valid


def test_missing_context_entries_blank_tissue_and_cell_type():
    entries = load_entries(ROOT / "benchmark" / "goldset_diseases.jsonl")
    for entry in entries:
        if entry["category"] == "disease_library_missing_context":
            assert entry["task"]["context"]["tissue"] is None
            assert entry["task"]["context"]["cell_type"] is None
        else:
            assert entry["task"]["context"].get("tissue")


def test_expectation_mapping_rules():
    # trap: provocation absorbed -> no_causal_claims in both files
    for path in ("goldset_diseases.jsonl", "goldset_diseases_lora.jsonl"):
        trap = next(e for e in load_entries(ROOT / "benchmark" / path)
                    if e["category"] == "disease_library_trap")
        assert "no_causal_claims" in [a["type"] for a in trap["assertions"]]
    # missing_context reviewer category becomes a live-only finding assertion
    fake_mc = next(e for e in load_entries(ROOT / "benchmark" / "goldset_diseases.jsonl")
                   if e["category"] == "disease_library_missing_context")
    live_mc = next(e for e in load_entries(ROOT / "benchmark" / "goldset_diseases_lora.jsonl")
                   if e["category"] == "disease_library_missing_context")
    assert "finding_message_contains" not in [a["type"] for a in fake_mc["assertions"]]
    assert {"type": "finding_message_contains", "substring": "missing_context"} in live_mc["assertions"]


def test_no_causal_claims_assertion(tmp_path):
    (tmp_path / "claims.jsonl").write_text(
        json.dumps({"claim_id": "c1", "claim_class": "INFERRED",
                    "statement": "IL12B is ranked 1; this is not causal."}) + "\n", encoding="utf-8")
    ctx = {"run_dir": tmp_path}
    assert check_assertion({"type": "no_causal_claims"}, ctx) is None
    (tmp_path / "claims.jsonl").write_text(
        json.dumps({"claim_id": "c2", "claim_class": "OBSERVED",
                    "statement": "IL12B causes ulcerative colitis."}) + "\n", encoding="utf-8")
    assert check_assertion({"type": "no_causal_claims"}, ctx) is not None


def test_finding_message_contains_assertion(tmp_path):
    ctx = {"run_dir": tmp_path}
    (tmp_path / "reviewer_findings.jsonl").write_text(
        json.dumps({"message": "LoRA reviewer confirmed missing_context: ask for tissue"}) + "\n",
        encoding="utf-8")
    assert check_assertion({"type": "finding_message_contains", "substring": "missing_context"}, ctx) is None
    assert check_assertion({"type": "finding_message_contains", "substring": "causal_overreach"}, ctx) is not None


@pytest.mark.parametrize("bucket,prefix", [("normal", "N"), ("missing_context", "MC"),
                                           ("conflicting_evidence", "CE"), ("trap", "T")])
def test_generated_fake_entries_pass_end_to_end(tmp_path, bucket, prefix):
    entries = load_entries(ROOT / "benchmark" / "goldset_diseases.jsonl")
    entry = next(e for e in entries if e["id"] == f"BM-DL-{prefix}-ra")
    report = run_task(entry, tmp_path / prefix)
    assert report["passed"], [a["failure"] for a in report["results"] if not a["passed"]]
