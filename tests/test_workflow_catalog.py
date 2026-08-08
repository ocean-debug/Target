"""Executable workflow template tests: catalog contracts, planner wiring and runtime gates."""
from __future__ import annotations

from pathlib import Path

import pytest

from target_agent.research_contracts import ResearchGoal, ResearchProjectSpec
from target_agent.research_planner import PlannerConfigurationError, ResearchPlanner
from target_agent.research_runtime import ResearchProjectRuntime
from target_agent.research_service import ResearchProjectService
from target_agent.workflow_catalog import WorkflowCatalog, WorkflowCatalogError, WorkflowModuleSpec, WorkflowTemplate

from .test_research_planner import BASELINE, StubModule, project, registry

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / "workflows"


def target_registry():
    return registry(StubModule("target_discovery"))


def target_project(*, workflow: str = "disease_to_target", sha256: str | None = None):
    spec = project(
        context={"target_task_spec": {"task_type": "disease_to_target"}},
        domain="disease_target_discovery",
    )
    template = WorkflowCatalog(WORKFLOWS_DIR).get(workflow)
    values = spec.model_dump(mode="json")
    values["workflow_template"] = template.template_id
    values["workflow_template_sha256"] = sha256 if sha256 is not None else template.source_sha256
    return ResearchProjectSpec.model_validate(values)


def test_catalog_loads_all_executable_templates_with_digests():
    catalog = WorkflowCatalog(WORKFLOWS_DIR)

    templates = catalog.list_templates()

    assert [row.template_id for row in templates] == ["disease_to_target", "literature_review"]
    for template in templates:
        assert len(template.source_sha256) == 64
        assert any(item.required for item in template.modules)
        assert {item.module for item in template.modules} >= {"project_brief", "independent_review", "research_report"}


def test_catalog_unknown_template_raises():
    catalog = WorkflowCatalog(WORKFLOWS_DIR)
    with pytest.raises(WorkflowCatalogError, match="unknown workflow template"):
        catalog.get("not_a_template")


def test_catalog_validate_plan_modules_rejects_outside_and_missing_required():
    catalog = WorkflowCatalog(WORKFLOWS_DIR)
    with pytest.raises(WorkflowCatalogError, match="outside template"):
        catalog.validate_plan_modules("literature_review", ["project_brief", "target_discovery"])
    with pytest.raises(WorkflowCatalogError, match="omits required"):
        catalog.validate_plan_modules("literature_review", ["project_brief"])


def test_template_validator_rejects_cycle_and_duplicate_modules():
    with pytest.raises(Exception):
        WorkflowTemplate(
            template_id="bad_cycle",
            description="cycle",
            modules=[
                WorkflowModuleSpec(module="a", required=True, dependencies=["b"]),
                WorkflowModuleSpec(module="b", required=True, dependencies=["a"]),
            ],
        )
    with pytest.raises(Exception):
        WorkflowTemplate(
            template_id="bad_duplicate",
            description="duplicate",
            modules=[
                WorkflowModuleSpec(module="a", required=True),
                WorkflowModuleSpec(module="a", required=False),
            ],
        )


def test_planner_disease_template_keeps_target_workflow_bounded():
    catalog = WorkflowCatalog(WORKFLOWS_DIR)
    planner = ResearchPlanner(target_registry(), workflow_catalog=catalog)

    plan = planner.deterministic(target_project(), "Step API not configured")

    assert [item.module for item in plan.items] == [
        "project_brief", "target_discovery", "independent_review", "research_report",
    ]
    assert plan.planner_backend.startswith("deterministic:research-v3")


def test_planner_literature_review_template_runs_generic_loop():
    catalog = WorkflowCatalog(WORKFLOWS_DIR)
    planner = ResearchPlanner(registry(), workflow_catalog=catalog)
    spec = ResearchProjectSpec(
        project_id="project-lit",
        title="Literature review",
        domain="life_science",
        goal=ResearchGoal(
            question="What is the evidence for IL-23 blockade in inflammatory bowel disease?",
            success_criteria=["Source-grounded conclusions."],
            deliverables=["A reviewed report."],
        ),
        workflow_template="literature_review",
        workflow_template_sha256=catalog.get("literature_review").source_sha256,
    )

    plan = planner.deterministic(spec, "Step API not configured")

    assert [item.module for item in plan.items] == BASELINE
    assert "target_discovery" not in [item.module for item in plan.items]


def test_planner_fails_closed_when_template_file_changes_after_freeze():
    catalog = WorkflowCatalog(WORKFLOWS_DIR)
    planner = ResearchPlanner(target_registry(), workflow_catalog=catalog)

    with pytest.raises(PlannerConfigurationError, match="changed after project freeze"):
        planner.deterministic(target_project(sha256="0" * 64), "Step API not configured")


def test_runtime_rejects_plan_from_a_different_template(tmp_path):
    catalog = WorkflowCatalog(WORKFLOWS_DIR)
    runtime = ResearchProjectRuntime(projects_dir=tmp_path / "projects")
    planner = ResearchPlanner(target_registry(), workflow_catalog=catalog)
    disease_plan = planner.deterministic(target_project(), "Step API not configured")

    runtime._validate_workflow_template(target_project(), disease_plan)

    lit_spec = ResearchProjectSpec(
        project_id="project-lit",
        title="Literature review",
        domain="life_science",
        goal=ResearchGoal(
            question="What is the evidence for IL-23 blockade in inflammatory bowel disease?",
            success_criteria=["Source-grounded conclusions."],
            deliverables=["A reviewed report."],
        ),
        workflow_template="literature_review",
        workflow_template_sha256=catalog.get("literature_review").source_sha256,
    )
    with pytest.raises(WorkflowCatalogError, match="outside template"):
        runtime._validate_workflow_template(lit_spec, disease_plan)


def test_service_builders_bind_workflow_template_and_digest(tmp_path):
    from .test_research_runtime import fake_research_runtime

    runtime, _ = fake_research_runtime(tmp_path)
    service = ResearchProjectService(runtime)

    generic = service.build_generic_project(
        question="Review the evidence for IL-23 blockade in IBD.",
        workflow="literature_review",
    )
    assert generic.workflow_template == "literature_review"
    assert len(generic.workflow_template_sha256) == 64
    assert generic.domain == "life_science"

    target = service.build_disease_project(
        question="Which targets are supported for ulcerative colitis?",
        disease="ulcerative colitis",
        workflow_template="disease_to_target",
    )
    assert target.workflow_template == "disease_to_target"
    assert len(target.workflow_template_sha256) == 64
    assert target.domain == "disease_target_discovery"

    rows = service.workflow_templates()
    assert {row["template_id"] for row in rows} == {"disease_to_target", "literature_review"}
    assert all("source_sha256" in row for row in rows)
def test_web_api_lists_workflow_templates(tmp_path):
    from .test_research_runtime import fake_research_runtime
    from .test_runtime import fake_runtime
    from target_agent.webapp import create_app

    research_runtime, _ = fake_research_runtime(tmp_path)
    app = create_app(fake_runtime(tmp_path), research_runtime=research_runtime)
    client = app.test_client()

    response = client.get("/api/workflows")

    assert response.status_code == 200
    rows = response.get_json()["workflows"]
    assert {row["template_id"] for row in rows} == {"disease_to_target", "literature_review"}
    assert all(len(row["source_sha256"]) == 64 for row in rows)
