from __future__ import annotations

import json

import pytest

from target_agent.llm import LLMUnavailable
from target_agent.research_contracts import DataContract, ResearchGoal, ResearchProjectSpec, WorkItemSpec
from target_agent.research_modules import ModuleDescriptor, ResearchModuleRegistry
from target_agent.research_planner import PlannerConfigurationError, ResearchPlanner


BASELINE = [
    "project_brief",
    "literature_search",
    "hypothesis_generation",
    "independent_review",
    "research_report",
]


class StubModule:
    def __init__(self, name: str, *, execution_policy: str = "typed_local"):
        self.descriptor = ModuleDescriptor(
            name=name,
            description=f"Typed test capability for {name}",
            input_types=("object",),
            output_types=("object",),
            execution_policy=execution_policy,
        )

    def execute(self, context):  # pragma: no cover - planner tests never execute modules
        raise AssertionError("module execution is outside planner scope")


class FakeClient:
    model = "step-test"

    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def json_completion(self, system: str, user: str):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.response


def registry(*extra: StubModule) -> ResearchModuleRegistry:
    return ResearchModuleRegistry([*(StubModule(name) for name in BASELINE), *extra])


def project(*, context=None, max_work_items: int = 12, domain: str = "life_science") -> ResearchProjectSpec:
    return ResearchProjectSpec(
        project_id="project-test",
        title="Traceable mechanism study",
        domain=domain,
        goal=ResearchGoal(
            question="Which disease mechanisms are supported by public evidence?",
            success_criteria=["Evidence-bearing conclusions are source traceable."],
            deliverables=["A reviewed research report."],
        ),
        context=context or {},
        max_work_items=max_work_items,
    )


def test_deterministic_plan_is_generic_and_review_gated():
    planner = ResearchPlanner(registry())

    plan = planner.deterministic(project(), "Step API not configured")

    assert [item.module for item in plan.items] == BASELINE
    review = next(item for item in plan.items if item.module == "independent_review")
    assert set(review.dependencies) == {
        "project_brief", "literature_search", "hypothesis_generation",
    }
    report = next(item for item in plan.items if item.module == "research_report")
    assert report.dependencies == [review.item_id]
    assert plan.project_id == "project-test"
    assert plan.planner_backend.startswith("deterministic:research-v3")
    assert all(item.output_contract is not None for item in plan.items)


def test_deterministic_plan_uses_bounded_target_workflow_when_requested():
    modules = registry(StubModule("target_discovery"))
    spec = project(context={"target_task_spec": {"task_type": "disease_to_target"}})

    plan = ResearchPlanner(modules).deterministic(spec)

    assert [item.module for item in plan.items] == [
        "project_brief", "target_discovery", "independent_review", "research_report",
    ]
    review = next(item for item in plan.items if item.module == "independent_review")
    assert "target_discovery" in review.dependencies
    target = next(item for item in plan.items if item.module == "target_discovery")
    assert target.max_attempts == 2


def test_vertical_product_always_plans_target_discovery_even_when_input_is_missing():
    modules = registry(StubModule("target_discovery"))

    plan = ResearchPlanner(modules).deterministic(project(domain="disease_target_discovery"))

    assert "target_discovery" in [item.module for item in plan.items]
    target = next(item for item in plan.items if item.module == "target_discovery")
    assert target.dependencies == ["project_brief"]

def test_step_plan_persists_evidence_strategy_patterns(tmp_path):
    from target_agent.paper_strategy import (
        EvidenceLink, PatternStore, SourcePaper, StrategyPattern,
    )

    store_path = tmp_path / "patterns.jsonl"
    store = PatternStore(store_path)
    store.add(StrategyPattern(
        pattern_id="pattern-test-ibd",
        name="IBD genetics-first strategy",
        disease_class="inflammatory bowel disease",
        disease_keywords=["crohn", "colitis", "ibd"],
        applicability=["disease with gwas and omics data"],
        evidence_start_lane="genetics",
        ordered_lanes=["genetics", "omics", "literature", "drug"],
        required_lanes=["genetics", "omics"],
        optional_lanes=["perturbation"],
        evidence_links=[EvidenceLink(
            link_id="genetics-to-omics", source_lane="genetics", target_lane="omics",
            link_type="colocalization", evidence_used=["gwas"], decision_rule="coloc>=0.8",
            why_this_link="Genetics anchors causality; omics resolves cell context.",
        )],
        stop_downgrade_rules=["no candidate without genetics support"],
        mixed_method_rationale="Genetics first, then context-resolved omics.",
        source_papers=[SourcePaper(title="IBD GWAS study", journal="Nature Genetics", year=2022)],
    ))

    modules = registry(StubModule("target_discovery"))
    base = ResearchPlanner(modules).deterministic(project(domain="disease_target_discovery"))
    client = FakeClient({
        "items": [item.model_dump(mode="json") for item in base.items],
        "rationale": "Genetics-first evidence strategy.",
    })
    spec = project(
        domain="disease_target_discovery",
        context={
            "target_task_spec": {
                "task_type": "disease_to_target",
                "context": {
                    "disease": "Crohn disease",
                    "gwas_available": True,
                    "preferred_dataset_accessions": ["GSE99999"],
                },
            }
        },
    )
    planner = ResearchPlanner(modules, client=client, pattern_store=store)

    plan = planner.create_plan(spec)

    assert plan.evidence_strategy_patterns
    assert plan.evidence_strategy_patterns[0]["pattern_id"] == "pattern-test-ibd"
    assert plan.evidence_strategy_patterns[0]["chosen_start"] == "genetics"
    assert plan.planner_backend.endswith("+pattern-fewshot:1")
    sent = json.loads(client.calls[0][1])
    assert sent["evidence_strategy_patterns"][0]["pattern_id"] == "pattern-test-ibd"


def test_step_plan_uses_live_registry_descriptors_and_strict_payload():
    modules = registry(StubModule("dataset_analysis"))
    base = ResearchPlanner(modules).deterministic(project())
    items = [item.model_dump(mode="json") for item in base.items]
    review = next(item for item in items if item["module"] == "independent_review")
    analysis = WorkItemSpec(
        item_id="dataset_analysis",
        title="Analyze a versioned dataset",
        module="dataset_analysis",
        objective="Run the registered typed dataset analysis module.",
        dependencies=["hypothesis_generation"],
        acceptance_criteria=["The dataset and analysis outputs remain versioned."],
        output_contract=DataContract(
            schema_id="DatasetAnalysisResult",
            required_fields=["artifact_count"],
            field_types={"artifact_count": "integer"},
        ),
    ).model_dump(mode="json")
    items.insert(items.index(review), analysis)
    review["dependencies"].append("dataset_analysis")
    client = FakeClient({"items": items, "rationale": "Use one additional registered analysis."})

    plan = ResearchPlanner(modules, client).create_plan(project())

    assert plan.planner_backend == "step:step-test"
    assert "dataset_analysis" in [item.module for item in plan.items]
    sent = json.loads(client.calls[0][1])
    assert {row["name"] for row in sent["registered_capabilities"]} == set(BASELINE) | {"dataset_analysis"}
    assert sent["max_work_items"] == 12


@pytest.mark.parametrize(
    "response",
    [
        {"items": [], "rationale": "Omit all safety gates."},
        {"items": [], "rationale": "Invalid", "project_id": "another-project"},
    ],
)
def test_invalid_or_extra_step_payload_falls_back_without_changing_project(response):
    planner = ResearchPlanner(registry(), FakeClient(response))

    plan = planner.create_plan(project())

    assert plan.project_id == "project-test"
    assert [item.module for item in plan.items] == BASELINE
    assert plan.planner_backend.endswith(("(ValueError)", "(ValidationError)"))


def test_non_whitelisted_and_shell_modules_never_enter_plan_or_prompt():
    modules = registry(StubModule("arbitrary_shell", execution_policy="shell_execution"))
    base = ResearchPlanner(registry()).deterministic(project())
    items = [item.model_dump(mode="json") for item in base.items]
    unsafe = WorkItemSpec(
        item_id="unsafe",
        title="Execute arbitrary shell",
        module="arbitrary_shell",
        objective="Execute model-generated commands.",
        dependencies=["hypothesis_generation"],
        acceptance_criteria=["Command exits."],
    ).model_dump(mode="json")
    items.insert(-2, unsafe)
    client = FakeClient({"items": items, "rationale": "Use a shell."})

    planner = ResearchPlanner(modules, client)
    plan = planner.create_plan(project())

    assert "arbitrary_shell" not in planner.allowed_modules
    assert "arbitrary_shell" not in [item.module for item in plan.items]
    sent = json.loads(client.calls[0][1])
    assert "arbitrary_shell" not in {row["name"] for row in sent["registered_capabilities"]}


def test_step_api_failure_uses_deterministic_workflow():
    client = FakeClient(error=LLMUnavailable("network unavailable"))

    plan = ResearchPlanner(registry(), client).create_plan(project())

    assert [item.module for item in plan.items] == BASELINE
    assert plan.planner_backend.endswith("(LLMUnavailable)")


def test_step_cannot_weaken_required_modules_or_typed_contracts():
    base = ResearchPlanner(registry()).deterministic(project())
    items = [item.model_dump(mode="json") for item in base.items]
    items[0]["required"] = False
    items[0]["output_contract"]["required_fields"] = []
    items[0]["output_contract"]["field_types"] = {}

    plan = ResearchPlanner(
        registry(), FakeClient({"items": items, "rationale": "Weaken the completion gate."}),
    ).create_plan(project())

    brief = next(item for item in plan.items if item.module == "project_brief")
    assert brief.required is True
    assert brief.output_contract.required_fields
    assert plan.planner_backend.endswith("(ValueError)")


def test_max_work_items_is_enforced_for_model_and_safe_baseline():
    baseline = ResearchPlanner(registry()).deterministic(project(max_work_items=5))
    items = [item.model_dump(mode="json") for item in baseline.items]
    extra = WorkItemSpec(
        item_id="extra",
        title="Extra typed search",
        module="literature_search",
        objective="Run an additional source retrieval.",
        dependencies=["project_brief"],
        acceptance_criteria=["Sources retain identifiers."],
    ).model_dump(mode="json")
    items.insert(-2, extra)
    review = next(item for item in items if item["module"] == "independent_review")
    review["dependencies"].append("extra")

    plan = ResearchPlanner(registry(), FakeClient({"items": items, "rationale": "Too many items."})).create_plan(
        project(max_work_items=5)
    )

    assert len(plan.items) == 5
    assert plan.planner_backend.endswith("(ValueError)")
    with pytest.raises(PlannerConfigurationError, match="cannot fit"):
        ResearchPlanner(registry(StubModule("target_discovery"))).deterministic(
            project(context={"target_task_spec": {}}, max_work_items=3)
        )


def test_missing_registered_baseline_module_fails_closed():
    incomplete = ResearchModuleRegistry([StubModule(name) for name in BASELINE if name != "independent_review"])

    with pytest.raises(PlannerConfigurationError, match="not registered"):
        ResearchPlanner(incomplete).create_plan(project())
