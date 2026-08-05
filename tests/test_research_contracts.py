from __future__ import annotations

import pytest
from pydantic import ValidationError

from target_agent.research_contracts import (
    DataContract, ResearchGoal, ResearchPlan, ResearchProjectSpec, WorkItemSpec,
)


def project() -> ResearchProjectSpec:
    return ResearchProjectSpec(
        project_id="project-contract",
        title="Disease target research",
        domain="disease_target_discovery",
        goal=ResearchGoal(
            question="Which targets should be prioritized for this disease?",
            success_criteria=["Every ranked target is evidence traceable."],
            deliverables=["Reviewed TargetCards"],
        ),
    )


def item(item_id: str, dependencies: list[str] | None = None) -> WorkItemSpec:
    return WorkItemSpec(
        item_id=item_id,
        title=f"Execute {item_id}",
        module="literature_search",
        objective="Produce a typed source-indexed result.",
        dependencies=dependencies or [],
        acceptance_criteria=["The output contract is satisfied."],
        output_contract=DataContract(
            schema_id="TestResult", required_fields=["count"], field_types={"count": "integer"},
        ),
    )


def test_research_plan_rejects_unknown_dependencies_and_cycles():
    with pytest.raises(ValidationError, match="unknown dependencies"):
        ResearchPlan(
            project_id=project().project_id, planner_backend="test", rationale="invalid",
            items=[item("one", ["missing"])],
        )
    with pytest.raises(ValidationError, match="dependency cycle"):
        ResearchPlan(
            project_id=project().project_id, planner_backend="test", rationale="invalid",
            items=[item("one", ["two"]), item("two", ["one"])],
        )


def test_data_contract_requires_declared_types_for_required_fields():
    with pytest.raises(ValidationError, match="no declared type"):
        DataContract(schema_id="Broken", required_fields=["count"])


def test_project_id_rejects_path_components():
    payload = project().model_dump(mode="json")
    payload["project_id"] = "../escape"
    with pytest.raises(ValidationError):
        ResearchProjectSpec.model_validate(payload)


def test_project_context_rejects_credentials_but_allows_scientific_key_names():
    payload = project().model_dump(mode="json")
    payload["context"] = {"cell_type_key": "cell_type", "nested": {"api_key": "must-not-persist"}}
    with pytest.raises(ValidationError, match="cannot contain credentials"):
        ResearchProjectSpec.model_validate(payload)

    payload["context"] = {"cell_type_key": "cell_type", "donor_key": "donor_id"}
    assert ResearchProjectSpec.model_validate(payload).context["cell_type_key"] == "cell_type"
