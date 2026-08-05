from __future__ import annotations

import pytest

from target_agent.contracts import GwasColumnMap, GwasSummaryStatsInput, TaskContext, TaskSpec
from target_agent.planner import Planner
from target_agent.tools.base import ScientificTool, ToolContext, ToolExecution, ToolRegistry


GENETICS_CHAIN = [
    ("genetics_input_audit", "genetics_input_audit", "scope"),
    ("fine_mapping_audit", "fine_mapping_audit", "genetics_input_audit"),
    ("eqtl_colocalization_audit", "eqtl_colocalization_audit", "fine_mapping_audit"),
    ("genetics_candidate_extraction", "genetics_candidate_extraction", "eqtl_colocalization_audit"),
]


class StubTool(ScientificTool):
    version = "test"

    def __init__(self, name: str):
        self.name = name

    def run(self, context: ToolContext) -> ToolExecution:  # pragma: no cover - planner-only fixture
        raise AssertionError("planner tests must not execute scientific tools")


def _registry() -> ToolRegistry:
    names = ["disease_resolver", *(tool for _, tool, _ in GENETICS_CHAIN)]
    return ToolRegistry([StubTool(name) for name in names])


def _gwas_input() -> GwasSummaryStatsInput:
    return GwasSummaryStatsInput(
        asset_id="gwas-planner-fixture",
        relative_path="planner/gwas.tsv",
        sha256="a" * 64,
        file_format="tsv",
        genome_build="GRCh38",
        study_id="GWAS-PLANNER-1",
        phenotype="lung adenocarcinoma",
        ancestry="EUR",
        sample_size=10_000,
        source_uri="https://example.org/gwas-planner-fixture",
        source_version="fixture-1",
        effect_scale="beta",
        columns=GwasColumnMap(
            chromosome="chromosome",
            position="position",
            effect_allele="effect_allele",
            other_allele="other_allele",
            effect="beta",
            standard_error="standard_error",
            p_value="p_value",
        ),
    )


def _task(task_type: str, *, with_genetics: bool) -> TaskSpec:
    return TaskSpec(
        task_type=task_type,
        question="Prioritize traceable targets for lung adenocarcinoma",
        context=TaskContext(
            disease="lung adenocarcinoma",
            organism="Homo sapiens",
            genome_build="GRCh38",
            ancestry="EUR",
        ),
        genetics_inputs=[_gwas_input()] if with_genetics else [],
    )


def _assert_fixed_chain(plan) -> None:
    by_id = {step.step_id: step for step in plan.steps}
    for step_id, tool, dependency in GENETICS_CHAIN:
        assert by_id[step_id].tool == tool
        assert by_id[step_id].dependencies == [dependency]


def test_gwas_locus_to_target_uses_the_fixed_genetics_dependency_chain():
    plan = Planner(None, _registry()).deterministic(
        _task("gwas_locus_to_target", with_genetics=True)
    )

    assert [step.tool for step in plan.steps if step.tool] == [
        "disease_resolver",
        "genetics_input_audit",
        "fine_mapping_audit",
        "eqtl_colocalization_audit",
        "genetics_candidate_extraction",
    ]
    assert "mch" not in {step.step_id for step in plan.steps}
    _assert_fixed_chain(plan)
    assert plan.planner_backend == "deterministic:v2.2"


def test_disease_to_target_without_genetics_does_not_inject_genetics_tools():
    plan = Planner(None, _registry()).deterministic(
        _task("disease_to_target", with_genetics=False)
    )

    planned_tools = {step.tool for step in plan.steps if step.tool}
    genetics_tools = {tool for _, tool, _ in GENETICS_CHAIN}
    assert planned_tools == {"disease_resolver"}
    assert planned_tools.isdisjoint(genetics_tools)


def test_disease_to_target_with_genetics_forces_the_fixed_chain():
    plan = Planner(None, _registry()).deterministic(
        _task("disease_to_target", with_genetics=True)
    )

    _assert_fixed_chain(plan)
    assert [step.tool for step in plan.steps if step.tool] == [
        "disease_resolver",
        "genetics_input_audit",
        "fine_mapping_audit",
        "eqtl_colocalization_audit",
        "genetics_candidate_extraction",
    ]


@pytest.mark.parametrize("task_type", ["disease_to_target", "gwas_locus_to_target"])
def test_genetics_workflow_refuses_registry_without_disease_resolver(task_type):
    registry = ToolRegistry([
        StubTool(tool) for _, tool, _ in GENETICS_CHAIN
    ])

    with pytest.raises(ValueError, match="disease_resolver"):
        Planner(None, registry).deterministic(
            _task(task_type, with_genetics=True)
        )


def test_llm_cannot_rewire_the_required_genetics_chain():
    class RewiringClient:
        model = "step-test"
        last_request_meta = {}

        def __init__(self):
            self.calls = 0

        def json_completion(self, system: str, user: str) -> dict:
            self.calls += 1
            return {
                "steps": [
                    {"step_id": "scope", "name": "Normalize", "tool": "disease_resolver"},
                    {
                        "step_id": "genetics_input_audit",
                        "name": "Input audit",
                        "tool": "genetics_input_audit",
                        "dependencies": ["scope"],
                    },
                    {
                        "step_id": "fine_mapping_audit",
                        "name": "Fine mapping audit",
                        "tool": "fine_mapping_audit",
                        "dependencies": ["genetics_input_audit"],
                    },
                    {
                        "step_id": "eqtl_colocalization_audit",
                        "name": "Colocalization audit",
                        "tool": "eqtl_colocalization_audit",
                        # Attempts to bypass the fine-mapping gate.
                        "dependencies": ["genetics_input_audit"],
                    },
                    {
                        "step_id": "genetics_candidate_extraction",
                        "name": "Candidate extraction",
                        "tool": "genetics_candidate_extraction",
                        "dependencies": ["eqtl_colocalization_audit"],
                    },
                ]
            }

    client = RewiringClient()
    plan = Planner(client, _registry()).create_plan(
        _task("gwas_locus_to_target", with_genetics=True)
    )

    assert client.calls == 2
    assert plan.fallback_used is True
    assert plan.planner_backend == "deterministic:v2.2 (ValueError)"
    _assert_fixed_chain(plan)
