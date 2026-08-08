from __future__ import annotations

import json

import pytest

from target_agent.research_contracts import ProjectStatus
from target_agent.research_service import ResearchProjectNotFound
from target_agent.research_session import (
    ResearchSessionService,
    ResearchSessionStore,
    SessionMessage,
)
from target_agent.webapp import create_app

from .test_research_runtime import fake_research_runtime, research_project
from .test_research_web_api import _wait_for_project
from .test_runtime import fake_runtime as fake_target_runtime


def _completed_runtime(tmp_path):
    runtime, _ = fake_research_runtime(tmp_path)
    project = research_project("project-session-store")
    terminal = runtime.run(project)
    assert terminal["status"] == ProjectStatus.COMPLETED.value
    return runtime, project


def test_session_store_roundtrip_and_tamper_detection(tmp_path):
    runtime, project = _completed_runtime(tmp_path)
    store = ResearchSessionStore(runtime.projects_dir)
    session = store.create_session(project.project_id, "研究对话")
    assert session.session_id.startswith("session-")
    assert store.list_sessions(project.project_id) == [session]

    message = store.append_message(
        project.project_id,
        SessionMessage(
            message_id="msg-abcdefabcdef",
            session_id=session.session_id,
            project_id=project.project_id,
            role="user",
            text="请总结当前进展",
            kind="question",
        ),
    )
    assert message.content_sha256 == message.digest()
    assert store.read_messages(project.project_id, session.session_id) == [message]

    ledger = runtime.projects_dir / project.project_id / "sessions" / f"{session.session_id}.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    rows[0]["text"] = "tampered"
    ledger.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="tampered"):
        store.read_messages(project.project_id, session.session_id)


def test_session_service_requires_existing_project_and_nonempty_text(tmp_path):
    runtime, project = _completed_runtime(tmp_path)
    service = ResearchSessionService(runtime)
    with pytest.raises(ResearchProjectNotFound):
        service.create("project-missing", title="x")
    session_id = service.create(project.project_id, title="x")["session"]["session_id"]
    with pytest.raises(ValueError):
        service.post_message(project.project_id, session_id, "   ")
    with pytest.raises(ResearchProjectNotFound):
        service.messages(project.project_id, "session-deadbeef1234")


def test_session_answer_is_deterministic_summary_not_scientific_state(tmp_path):
    runtime, project = _completed_runtime(tmp_path)
    service = ResearchSessionService(runtime)
    session_id = service.create(project.project_id, title="进展询问")["session"]["session_id"]

    first = service.post_message(project.project_id, session_id, "现在到哪一步了？", ask_agent=True)
    second = service.post_message(project.project_id, session_id, "现在到哪一步了？", ask_agent=True)
    assert [m["role"] for m in first["messages"]] == ["user", "assistant"]
    assert first["messages"][0]["kind"] == "question"
    assert first["messages"][1]["source_bound"] is False
    assert first["messages"][1]["references"] == [f"project:{project.project_id}"]
    assert first["messages"][1]["text"] == second["messages"][1]["text"]
    assert "当前状态" in first["messages"][1]["text"]
    assert "执行计划" in first["messages"][1]["text"]

    listed = service.list(project.project_id)
    assert len(listed["sessions"]) == 1
    assert listed["sessions"][0]["message_count"] == 4
    assert len(service.messages(project.project_id, session_id)["messages"]) == 4


def test_session_web_endpoints_create_read_and_post(tmp_path):
    research_runtime, _ = fake_research_runtime(tmp_path)
    client = create_app(
        fake_target_runtime(tmp_path),
        research_runtime=research_runtime,
    ).test_client()
    project = research_project("project-session-web")
    assert client.post("/api/projects", json=project.model_dump(mode="json")).status_code == 202
    _wait_for_project(client, project.project_id)

    created = client.post(f"/api/projects/{project.project_id}/sessions", json={"title": "对话"})
    assert created.status_code == 201
    session_id = created.get_json()["session"]["session_id"]

    listing = client.get(f"/api/projects/{project.project_id}/sessions")
    assert listing.status_code == 200
    assert listing.get_json()["sessions"][0]["message_count"] == 0

    posted = client.post(
        f"/api/projects/{project.project_id}/sessions/{session_id}/messages",
        json={"text": "下一步建议？", "ask_agent": True},
    )
    assert posted.status_code == 200
    assert [m["role"] for m in posted.get_json()["messages"]] == ["user", "assistant"]
    assert posted.get_json()["messages"][1]["source_bound"] is False

    read = client.get(f"/api/projects/{project.project_id}/sessions/{session_id}")
    assert read.status_code == 200
    assert len(read.get_json()["messages"]) == 2

    assert (
        client.get(
            f"/api/projects/{project.project_id}/sessions/session-deadbeef1234"
        ).status_code
        == 404
    )
    empty = client.post(
        f"/api/projects/{project.project_id}/sessions/{session_id}/messages",
        json={"text": "  "},
    )
    assert empty.status_code == 400