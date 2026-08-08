from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import jsonschema

from benchmark.evaluate_context_relations import evaluate
from benchmark.generate_context_relation_goldset import build_entries, render, validate

ROOT = Path(__file__).resolve().parents[1]
GOLDSET = ROOT / "benchmark" / "goldset_context_relations.jsonl"
SCHEMA = ROOT / "schemas" / "context_relation_case.schema.json"


def test_generated_goldset_is_current_and_schema_valid():
    entries = build_entries()
    validate(entries)
    assert GOLDSET.read_text(encoding="utf-8") == render(entries)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for entry in entries:
        jsonschema.validate(entry, schema)


def test_expected_coverage_and_relation_families():
    entries = build_entries()
    counts = Counter(entry["task_family"] for entry in entries)
    assert counts == {"disease_target_anchor": 73, "contextualized_target": 72}
    labels = Counter(entry["gold"]["label"] for entry in entries)
    assert labels == {
        "supported_anchor": 73,
        "context_complete": 18,
        "insufficient_context": 18,
        "context_mismatch": 36,
    }


def test_disease_and_context_donors_do_not_cross_splits():
    entries = build_entries()
    disease_splits: dict[str, set[str]] = defaultdict(set)
    id_to_split = {
        entry["provenance"][0]["locator"].split("[")[1].split("]")[0]: entry["split"]
        for entry in entries
    }
    for entry in entries:
        disease_splits[entry["query"]["disease_id"]].add(entry["split"])
        donor = entry.get("perturbation", {}).get("donor_disease_id")
        if donor:
            assert id_to_split[donor] == entry["split"]
    assert all(len(splits) == 1 for splits in disease_splits.values())
    assert set().union(*disease_splits.values()) == {"train", "validation", "test"}


def test_perfect_predictions_score_one():
    gold = build_entries()
    predictions = [{
        "id": entry["id"],
        "label": entry["gold"]["label"],
        "actions": entry["gold"]["required_actions"],
        "claims": [],
    } for entry in gold]
    report = evaluate(gold, predictions)
    assert report["duplicate_prediction_ids"] == 0
    assert not report["failures"]
    assert set(report["metrics"].values()) == {1.0}
