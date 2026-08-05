from __future__ import annotations

import time

from target_agent.webapp import create_app

from .test_research_runtime import fake_research_runtime, research_project
from .test_runtime import fake_runtime as fake_target_runtime


def _wait_for_project(client, project_id: str, timeout_seconds: float = 3.0):
    deadline = time.monotonic() + timeout_seconds
    latest = None
    while time.monotonic() < deadline:
        latest = client.get(f"/api/projects/{project_id}")
        if latest.status_code == 200:
            state = latest.get_json().get("state") or {}
            if state.get("status") in {"completed", "completed_with_gaps", "needs_input", "failed"}:
                return latest
        time.sleep(0.01)
    raise AssertionError(
        f"project {project_id} did not reach a terminal state; "
        f"last status was {None if latest is None else latest.status_code}"
    )


def test_project_post_get_events_and_artifact_download_use_durable_state(tmp_path):
    research_runtime, calls = fake_research_runtime(tmp_path)
    app = create_app(
        fake_target_runtime(tmp_path),
        research_runtime=research_runtime,
    )
    client = app.test_client()
    project = research_project("project-web-api")

    created = client.post("/api/projects", json=project.model_dump(mode="json"))

    assert created.status_code == 202
    assert created.get_json() == {
        "project_id": project.project_id,
        "status_url": f"/api/projects/{project.project_id}",
        "events_url": f"/api/projects/{project.project_id}/events",
    }
    response = _wait_for_project(client, project.project_id)
    payload = response.get_json()
    assert payload["contract_version"] == "3.0.0"
    assert payload["spec"]["goal"]["question"] == project.goal.question
    assert payload["state"]["status"] == "completed"
    assert len(payload["plan"]["items"]) == 5
    assert len(payload["work_item_results"]) == 5
    assert calls["research_report"] == 1

    events = client.get(f"/api/projects/{project.project_id}/events")
    assert events.status_code == 200
    event_rows = events.get_json()["events"]
    assert [row["sequence"] for row in event_rows] == list(range(1, len(event_rows) + 1))
    assert event_rows[-1]["event_type"] == "project_terminal"
    tail = client.get(
        f"/api/projects/{project.project_id}/events?after_sequence={event_rows[-2]['sequence']}"
    ).get_json()
    assert tail["events"] == [event_rows[-1]]
    assert tail["next_cursor"] == event_rows[-1]["sequence"]

    activities = client.get(f"/api/projects/{project.project_id}/activities")
    assert activities.status_code == 200
    assert activities.get_json() == {
        "contract_version": "3.0.0",
        "project_id": project.project_id,
        "activities": [],
        "next_cursor": 0,
        "has_more": False,
    }

    report = next(row for row in payload["artifacts"] if row["logical_name"] == "research_report")
    downloaded = client.get(
        f"/api/projects/{project.project_id}/artifacts/{report['artifact_id']}"
    )
    assert downloaded.status_code == 200
    assert downloaded.mimetype == "text/markdown"
    assert downloaded.get_data(as_text=True).startswith("# Fake research report")


def test_project_api_rejects_invalid_payload_and_duplicate_project(tmp_path):
    research_runtime, _ = fake_research_runtime(tmp_path)
    client = create_app(
        fake_target_runtime(tmp_path),
        research_runtime=research_runtime,
    ).test_client()

    invalid = client.post("/api/projects", json={"title": "missing goal"})
    assert invalid.status_code == 400
    assert invalid.get_json()["error"] == "invalid ResearchProjectSpec"

    project = research_project("project-web-duplicate")
    assert client.post("/api/projects", json=project.model_dump(mode="json")).status_code == 202
    _wait_for_project(client, project.project_id)
    duplicate = client.post("/api/projects", json=project.model_dump(mode="json"))
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"] == "project id already exists"


def test_project_api_missing_resources_are_explicit(tmp_path):
    research_runtime, _ = fake_research_runtime(tmp_path)
    client = create_app(
        fake_target_runtime(tmp_path),
        research_runtime=research_runtime,
    ).test_client()

    assert client.get("/api/projects/project-does-not-exist").status_code == 404
    assert client.get("/api/projects/project-does-not-exist/events").status_code == 404
    assert client.get("/api/projects/project-does-not-exist/activities").status_code == 404
    assert client.get("/api/projects/project-does-not-exist/events?after_sequence=bad").status_code == 400
    assert (
        client.get("/api/projects/project-does-not-exist/artifacts/artifact-missing").status_code
        == 404
    )
