from __future__ import annotations

import asyncio
from importlib.metadata import version

import pytest
import target_agent

from target_agent.research_contracts import ProjectStatus
from target_agent.research_service import (
    ResearchDecisionError,
    ResearchProjectNotFound,
    ResearchProjectService,
)

from .test_research_runtime import fake_research_runtime


def _service(tmp_path):
    runtime, calls = fake_research_runtime(tmp_path)
    return ResearchProjectService(runtime), calls


def test_public_package_version_matches_distribution_metadata():
    assert target_agent.__version__ == version("target-discovery-agent") == "0.6.0"


def test_service_advances_one_disease_question_to_durable_deliverables(tmp_path):
    service, calls = _service(tmp_path)
    project = service.build_disease_project(
        project_id="project-mcp-autonomous",
        question="Which disease-driving targets should be prioritized for lung adenocarcinoma?",
        disease="lung adenocarcinoma",
        tissue="lung",
        cell_type="malignant epithelial cell",
        autonomy_mode="autonomous",
    )

    reserved = service.reserve(project)
    assert reserved["created"] is True
    assert reserved["project"]["state"] is None
    assert reserved["project"]["next_actions"] == [
        {"action": "run_project", "project_id": project.project_id}
    ]

    terminal = service.run(project.project_id)

    assert terminal["state"]["status"] == ProjectStatus.COMPLETED.value
    assert terminal["event_cursor"] > 0
    assert terminal["next_actions"] == [
        {"action": "inspect_artifacts", "project_id": project.project_id}
    ]
    assert calls["target_discovery"] == 1
    assert {row["logical_name"] for row in terminal["artifacts"]} >= {
        "project_brief_output",
        "target_discovery_output",
        "independent_review_output",
        "research_report",
    }
    assert terminal["decisions"][-1]["action"] == "release"


def test_service_exposes_real_checkpoint_progression_and_event_cursor(tmp_path):
    service, calls = _service(tmp_path)
    project = service.build_disease_project(
        project_id="project-mcp-checkpointed",
        question="Which targets should be tested next in ulcerative colitis?",
        disease="ulcerative colitis",
        tissue="colon",
        autonomy_mode="checkpointed",
    )
    service.reserve(project)

    waiting_plan = service.run(project.project_id)
    plan_id = waiting_plan["plan"]["plan_id"]
    assert waiting_plan["state"]["status"] == ProjectStatus.NEEDS_INPUT.value
    assert waiting_plan["next_actions"][0]["target_id"] == plan_id
    assert not calls

    waiting_release = service.accept_checkpoint(
        project_id=project.project_id,
        target_id=plan_id,
        actor="scientific-review-role",
        rationale="The evidence scope and budgets are appropriate.",
        resume=True,
    )["project"]
    release_target = f"release:{plan_id}"
    assert waiting_release["state"]["status"] == ProjectStatus.WAITING_REVIEW.value
    assert waiting_release["next_actions"][0]["target_id"] == release_target

    completed = service.accept_checkpoint(
        project_id=project.project_id,
        target_id=release_target,
        actor="scientific-review-role",
        rationale="The digest-bound deliverables passed release review.",
        resume=True,
    )["project"]
    assert completed["state"]["status"] == ProjectStatus.COMPLETED.value
    assert calls["target_discovery"] == 1

    first_page = service.events(project.project_id, after_sequence=0)
    second_page = service.events(project.project_id, after_sequence=first_page[-2]["sequence"])
    assert second_page[0]["sequence"] == first_page[-1]["sequence"]


def test_service_does_not_infer_missing_biological_context(tmp_path):
    service, _ = _service(tmp_path)
    project = service.build_disease_project(
        question="Find targets for a disease with incomplete context.",
        disease="Alzheimer disease",
    )
    context = project.context["target_task_spec"]["context"]

    assert context["disease"] == "Alzheimer disease"
    assert context["tissue"] is None
    assert context["cell_type"] is None
    assert context["disease_stage"] is None
    assert context["desired_phenotype"] is None


def test_service_rejects_unknown_projects_and_unfrozen_decisions(tmp_path):
    service, _ = _service(tmp_path)
    with pytest.raises(ResearchProjectNotFound, match="project not found"):
        service.snapshot("project-unknown")

    project = service.build_disease_project(
        project_id="project-no-plan",
        question="Which targets should be prioritized?",
        disease="Alzheimer disease",
    )
    service.reserve(project)
    with pytest.raises(ResearchDecisionError, match="frozen plan"):
        service.accept_checkpoint(
            project_id=project.project_id,
            target_id="made-up",
            actor="reviewer",
            rationale="This must fail closed.",
        )


def test_official_mcp_sdk_exposes_the_same_durable_service(tmp_path):
    mcp = pytest.importorskip("mcp")
    from target_agent.mcp_server import create_mcp_server

    service, _ = _service(tmp_path)
    server = create_mcp_server(service)

    async def exercise():
        async with mcp.Client(server) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {
                "target_capabilities",
                "target_create_disease_project",
                "target_run_project",
                "target_get_project",
                "target_list_projects",
                "target_get_events",
                "target_accept_checkpoint",
                "target_read_text_artifact",
            } <= names
            created = await client.call_tool(
                "target_create_disease_project",
                {
                    "project_id": "project-mcp-protocol",
                    "question": "Which targets should be prioritized for lung adenocarcinoma?",
                    "disease": "lung adenocarcinoma",
                    "tissue": "lung",
                    "autonomy_mode": "autonomous",
                },
            )
            assert created.structured_content["created"] is True
            finished = await client.call_tool(
                "target_run_project", {"project_id": "project-mcp-protocol"}
            )
            assert finished.structured_content["state"]["status"] == "completed"

    asyncio.run(exercise())
