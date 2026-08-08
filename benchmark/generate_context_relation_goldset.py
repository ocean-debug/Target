"""Generate a disease-target-context relationship benchmark.

The committed JSONL is derived only from the curated disease library. It has
two task families: disease/target sanity anchors and contextualized target
cases covering tissue, cell type, and disease stage.

Context perturbations are not biological negative labels. They only test
whether a system notices that a query differs from the curated benchmark
context. All cases for one disease stay in one split.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from target_agent.diseases import DiseaseEntry, load_library  # noqa: E402

OUT = ROOT / "benchmark" / "goldset_context_relations.jsonl"

# Disease-disjoint splits. Context donors stay inside a split so a train
# perturbation never exposes the canonical context of a held-out disease.
VALIDATION_DISEASES = {"t1d", "pd", "melanoma", "asthma"}
TEST_DISEASES = {"psoriasis", "als", "crc", "nash"}


def split_for(disease_id: str) -> str:
    if disease_id in VALIDATION_DISEASES:
        return "validation"
    if disease_id in TEST_DISEASES:
        return "test"
    return "train"


def stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"CR-{digest.upper()}"


def context_payload(disease: DiseaseEntry) -> dict[str, str | None]:
    return disease.context.model_dump(mode="json")


def provenance(disease: DiseaseEntry, target_index: int) -> list[dict[str, Any]]:
    return [{
        "source_type": "curated_repository_config",
        "source_uri": "configs/disease_library.yaml",
        "locator": f"diseases[{disease.id}].reference_targets[{target_index}]",
        "curation_scope": "disease-level ranking sanity anchor",
    }]


def anchor_case(disease: DiseaseEntry, target_index: int) -> dict[str, Any]:
    target = disease.reference_targets[target_index]
    return {
        "id": stable_id("anchor", disease.id, target.gene),
        "split": split_for(disease.id),
        "task_family": "disease_target_anchor",
        "relation_type": "disease_target",
        "query": {
            "disease": disease.name,
            "disease_id": disease.ontology_id,
            "target": target.gene,
            "context": context_payload(disease),
        },
        "gold": {
            "label": "supported_anchor",
            "evidence_level": target.evidence,
            "required_actions": ["preserve_context", "trace_evidence"],
            "forbidden_claims": ["context_specific_causality", "clinical_success_probability"],
            "claim_boundary": (
                "The target is a curated disease-level ranking anchor; the record alone does not "
                "establish cell-specific causality or therapeutic efficacy."
            ),
        },
        "provenance": provenance(disease, target_index),
    }


def contextual_case(
    disease: DiseaseEntry,
    target_index: int,
    variant: str,
    donor: DiseaseEntry | None = None,
) -> dict[str, Any]:
    target = disease.reference_targets[target_index]
    context = context_payload(disease)
    required_actions = ["preserve_context", "trace_evidence"]
    label = "context_complete"
    changed_fields: list[str] = []

    if variant == "missing_cell_type":
        context["cell_type"] = None
        label = "insufficient_context"
        changed_fields = ["cell_type"]
        required_actions = ["request_or_degrade_missing_context", "trace_evidence"]
    elif variant == "tissue_swap":
        if donor is None:
            raise ValueError("tissue_swap requires a donor")
        context["tissue"] = donor.context.tissue
        label = "context_mismatch"
        changed_fields = ["tissue"]
        required_actions = ["flag_context_mismatch", "avoid_context_specific_causal_claim"]
    elif variant == "stage_swap":
        if donor is None:
            raise ValueError("stage_swap requires a donor")
        context["disease_stage"] = donor.context.disease_stage
        label = "context_mismatch"
        changed_fields = ["disease_stage"]
        required_actions = ["flag_context_mismatch", "avoid_context_specific_causal_claim"]
    elif variant != "complete":
        raise ValueError(f"unknown context variant: {variant}")

    return {
        "id": stable_id("context", disease.id, target.gene, variant),
        "split": split_for(disease.id),
        "task_family": "contextualized_target",
        "relation_type": "disease_target_tissue_cell_stage",
        "query": {
            "disease": disease.name,
            "disease_id": disease.ontology_id,
            "target": target.gene,
            "context": context,
        },
        "perturbation": {
            "kind": variant,
            "changed_fields": changed_fields,
            "donor_disease_id": donor.id if donor else None,
            "interpretation": (
                "Benchmark-context perturbation; not evidence that the biological relation is false."
            ),
        },
        "gold": {
            "label": label,
            "evidence_level": target.evidence,
            "required_actions": required_actions,
            "forbidden_claims": ["context_specific_causality", "biological_relation_is_false"],
            "claim_boundary": (
                "Judge agreement with the curated task context, not universal biological validity."
            ),
        },
        "provenance": provenance(disease, target_index),
    }


def _context_donors(diseases: list[DiseaseEntry]) -> dict[str, DiseaseEntry]:
    by_split: dict[str, list[DiseaseEntry]] = defaultdict(list)
    for disease in diseases:
        by_split[split_for(disease.id)].append(disease)
    donors: dict[str, DiseaseEntry] = {}
    for members in by_split.values():
        for index, disease in enumerate(members):
            candidates = members[index + 1:] + members[:index]
            donor = next(
                (item for item in candidates
                 if item.context.tissue != disease.context.tissue
                 and item.context.disease_stage != disease.context.disease_stage),
                None,
            )
            if donor is None:
                raise ValueError(f"no distinct same-split context donor for {disease.id}")
            donors[disease.id] = donor
    return donors


def build_entries() -> list[dict[str, Any]]:
    diseases = load_library().diseases
    donors = _context_donors(diseases)
    entries: list[dict[str, Any]] = []
    for disease in diseases:
        for target_index in range(len(disease.reference_targets)):
            entries.append(anchor_case(disease, target_index))
        # One representative target per disease keeps the context family
        # balanced across diseases rather than target-list length.
        for variant in ("complete", "missing_cell_type", "tissue_swap", "stage_swap"):
            entries.append(contextual_case(
                disease,
                target_index=0,
                variant=variant,
                donor=donors[disease.id] if variant.endswith("swap") else None,
            ))
    return sorted(entries, key=lambda item: item["id"])


def render(entries: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n" for entry in entries)


def validate(entries: list[dict[str, Any]]) -> None:
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids")
    disease_splits: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        disease_splits[entry["query"]["disease_id"]].add(entry["split"])
        donor_id = entry.get("perturbation", {}).get("donor_disease_id")
        if donor_id and split_for(donor_id) != entry["split"]:
            raise ValueError(f"cross-split context donor in {entry['id']}")
    leaked = {disease_id: splits for disease_id, splits in disease_splits.items() if len(splits) != 1}
    if leaked:
        raise ValueError(f"disease leakage across splits: {leaked}")


def summary(entries: list[dict[str, Any]]) -> str:
    splits = Counter(entry["split"] for entry in entries)
    families = Counter(entry["task_family"] for entry in entries)
    labels = Counter(entry["gold"]["label"] for entry in entries)
    return f"{len(entries)} cases; splits={dict(splits)}; families={dict(families)}; labels={dict(labels)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when the committed JSONL is stale")
    args = parser.parse_args()
    entries = build_entries()
    validate(entries)
    content = render(entries)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            print(f"stale goldset: {OUT}; run python benchmark/generate_context_relation_goldset.py")
            return 1
        print(f"goldset is up to date: {summary(entries)}")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT}: {summary(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
