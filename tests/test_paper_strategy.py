"""Pattern contract, store, retrieval and planner few-shot tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from target_agent.paper_strategy import (
    BestPracticePattern, PatternStore, PlannerFewShotBuilder, StrategyPattern,
    infer_data_availability,
)


def _base_pattern(overrides=None):
    data = {
        "pattern_id": "pattern-test-genetics-first",
        "name": "Genetics-first test pattern",
        "disease_class": "test disease",
        "disease_keywords": ["test"],
        "applicability": ["GWAS data available"],
        "evidence_start_lane": "genetics",
        "ordered_lanes": ["genetics", "omics", "literature"],
        "required_lanes": ["genetics", "omics"],
        "optional_lanes": ["literature"],
        "evidence_links": [{
            "link_id": "link-1", "source_lane": "genetics", "target_lane": "omics",
            "link_type": "gwas_to_eqtl", "evidence_used": ["eQTL"],
            "decision_rule": "coloc PP4 threshold", "why_this_link": "anchor variant to gene",
        }],
        "stop_downgrade_rules": ["Do not promote variant-only hits"],
        "mixed_method_rationale": "GWAS power first, then eQTL anchor.",
        "source_papers": [{"title": "Test paper", "journal": "Nature", "year": 2023}],
    }
    if overrides:
        data.update(overrides)
    return StrategyPattern.model_validate(data)


def test_schema_rejects_missing_stop_rules():
    with pytest.raises(ValueError):
        _base_pattern({"stop_downgrade_rules": []})


def test_schema_requires_start_lane_in_ordered():
    with pytest.raises(ValueError):
        _base_pattern({"evidence_start_lane": "perturbation"})


def test_schema_rejects_duplicate_lanes():
    with pytest.raises(ValueError):
        _base_pattern({"ordered_lanes": ["genetics", "genetics", "omics"]})


def test_best_practice_requires_validation_refs():
    data = _base_pattern({}).model_dump(mode="json")
    data.pop("digest", None)
    data.update({
        "validation_level": "best_practice",
        "validated_by": ["expert_panel"],
        "validation_refs": ["benchmark/rubric.md"],
    })
    best = BestPracticePattern.model_validate(data)
    assert best.validation_level == "best_practice"
    assert len(best.validation_refs) == 1


def test_store_add_is_immutable_and_deduplicates(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    assert store.add(_base_pattern())
    assert not store.add(_base_pattern())
    assert store.get("pattern-test-genetics-first") is not None
    with pytest.raises(ValueError):
        store.add(_base_pattern({
            "pattern_id": "pattern-test-tampered",
            "digest": "0" * 64,
        }))


def test_store_parses_seed_corpus():
    store = PatternStore(Path(__file__).resolve().parents[1] / "paper_strategy" / "patterns.jsonl")
    rows = store.all()
    assert len(rows) >= 10
    assert all(row.digest == row.compute_digest() for row in rows)


def test_search_prefers_matching_disease_and_available_lanes(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    store.add(_base_pattern())
    store.add(_base_pattern({
        "pattern_id": "pattern-test-perturbation-first",
        "name": "Perturbation-first test pattern",
        "disease_class": "other disease",
        "evidence_start_lane": "perturbation",
        "ordered_lanes": ["perturbation", "genetics", "literature"],
        "required_lanes": ["perturbation", "genetics"],
        "optional_lanes": ["literature"],
    }))
    hits = store.search(disease="test disease", lanes_available=["genetics", "omics", "literature"])
    assert hits
    assert hits[0].pattern.pattern_id == "pattern-test-genetics-first"


def test_search_penalizes_unavailable_required_lanes(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    store.add(_base_pattern())
    hits = store.search(disease="test disease", lanes_available=["literature"])
    assert not hits  # required genetics/omics unavailable pushes score below threshold


def test_few_shot_builder_returns_rationale(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    store.add(_base_pattern())
    builder = PlannerFewShotBuilder(store, top_k=2)
    shots = builder.build(
        disease="test disease",
        data_availability={"genetics": True, "omics": True, "literature": True},
    )
    assert shots
    assert shots[0]["strategy_hint_not_evidence"] is True
    assert shots[0]["why_this_order"]


def test_few_shot_empty_without_store():
    assert PlannerFewShotBuilder(None, top_k=3).build(disease="x") == []


def test_infer_data_availability():
    assert infer_data_availability({}) is None

def test_planner_injects_few_shot_patterns(tmp_path):
    import json

    from target_agent.research_contracts import ResearchGoal, ResearchProjectSpec
    from target_agent.research_modules import ModuleDescriptor, ResearchModuleRegistry
    from target_agent.research_planner import ResearchPlanner

    class StubModule:
        def __init__(self, name: str):
            self.descriptor = ModuleDescriptor(
                name=name, description=f"Typed test capability for {name}",
                input_types=("object",), output_types=("object",),
                execution_policy="typed_local",
            )

        def execute(self, context):  # pragma: no cover - planner test
            raise AssertionError("module execution is outside planner scope")

    names = (
        "project_brief", "literature_search", "hypothesis_generation",
        "independent_review", "research_report", "target_discovery",
    )
    modules = ResearchModuleRegistry([StubModule(name) for name in names])
    store = PatternStore(tmp_path / "patterns.jsonl")
    store.add(_base_pattern())

    spec = ResearchProjectSpec(
        project_id="project-test",
        title="Test disease target discovery",
        domain="disease_target_discovery",
        goal=ResearchGoal(
            question="Find targets for the test disease",
            success_criteria=["Evidence-bearing conclusions are source traceable."],
            deliverables=["A reviewed research report."],
        ),
        context={
            "target_task_spec": {
                "task_type": "disease_to_target",
                "context": {
                    "disease": "test disease",
                    "gwas_summary_stats": "fixtures/gwas.tsv",
                    "preferred_dataset_accessions": ["GSE1"],
                },
            }
        },
        max_work_items=12,
    )
    template = ResearchPlanner(modules).deterministic(spec)
    items = [item.model_dump(mode="json") for item in template.items]

    class FakeClient:
        model = "step-test"

        def __init__(self):
            self.calls: list[tuple[str, str]] = []

        def json_completion(self, system: str, user: str):
            self.calls.append((system, user))
            return {"items": items, "rationale": "Use retrieved strategy patterns."}

    client = FakeClient()
    planner = ResearchPlanner(modules, client, pattern_store=store, few_shot_top_k=2)
    plan = planner.create_plan(spec)

    sent = json.loads(client.calls[0][1])
    patterns = sent["evidence_strategy_patterns"]
    assert patterns
    assert patterns[0]["strategy_hint_not_evidence"] is True
    assert patterns[0]["chosen_start"] == "genetics"
    assert "pattern-fewshot" in plan.planner_backend
    assert plan.project_id == "project-test"
    avail = infer_data_availability({"disease": "x", "preferred_dataset_accessions": ["GSE1"]})
    assert avail is not None
    assert avail["omics"] is True
    assert avail["genetics"] is False

def test_domain_planner_injects_pattern_hints(tmp_path):
    import json

    from target_agent.contracts import TaskSpec
    from target_agent.planner import Planner
    from target_agent.tools.base import ToolRegistry

    from fakes import FakeGenericOmics, FakeLiterature, FakeOpenTargets

    store = PatternStore(tmp_path / "patterns.jsonl")
    store.add(_base_pattern({
        "pattern_id": "pattern-test-ibd",
        "name": "IBD genetics-first test pattern",
        "disease_class": "ulcerative colitis",
        "disease_keywords": ["colitis", "ibd"],
    }))

    class FakeClient:
        model = "step-test"
        last_request_meta: dict = {}

        def __init__(self):
            self.last_user = ""

        def json_completion(self, system: str, user: str) -> dict:
            self.last_user = user
            payload = json.loads(user)
            return payload["required_template"]

    client = FakeClient()
    registry = ToolRegistry([FakeGenericOmics(), FakeOpenTargets(), FakeLiterature()])
    planner = Planner(client, registry, pattern_store=store, few_shot_top_k=2)
    task = TaskSpec(
        task_type="disease_to_target",
        question="Discover traceable targets for ulcerative colitis",
        context={"disease": "ulcerative colitis", "tissue": "rectum", "cell_type": "T cell"},
    )
    plan = planner.create_plan(task)
    assert planner.last_pattern_hints
    assert planner.last_pattern_hints[0]["pattern_id"] == "pattern-test-ibd"
    assert "+pattern-fewshot:1" in plan.planner_backend
    sent = json.loads(client.last_user)
    assert sent["pattern_hints"][0]["strategy_hint_not_evidence"] is True
    assert "pattern_hints" in sent

    # without a store the domain planner emits no hints and stays deterministic-safe
    plain = Planner(client, registry, pattern_store=None)
    plain.create_plan(task)
    assert plain.last_pattern_hints == []

