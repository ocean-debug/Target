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

def test_session_intervention_forwards_accept_checkpoint_and_records_ledger(tmp_path, monkeypatch):
    runtime, project = _completed_runtime(tmp_path)
    service = ResearchSessionService(runtime)
    session_id = service.create(project.project_id, title="干预")["session"]["session_id"]

    captured = {}

    def fake_accept(*, project_id, target_id, actor, rationale, resume=False):
        captured.update(project_id=project_id, target_id=target_id, actor=actor, rationale=rationale)
        return {
            "decision": {
                "decision_id": "decision-abcdefabcdef",
                "action": "accept",
                "target_ids": [target_id],
            },
            "project": {},
        }

    monkeypatch.setattr(service.projects_service, "accept_checkpoint", fake_accept)
    result = service.intervene(
        project.project_id,
        session_id,
        action="accept_checkpoint",
        rationale="证据充分，批准继续",
        actor="reviewer",
        target_id="plan-xyz",
    )
    assert captured == {
        "project_id": project.project_id,
        "target_id": "plan-xyz",
        "actor": "reviewer",
        "rationale": "证据充分，批准继续",
    }
    assert result["decision"]["decision_id"] == "decision-abcdefabcdef"
    assert [m["kind"] for m in result["messages"]] == ["intervention", "intervention_result"]
    assert result["messages"][1]["role"] == "system"
    assert result["messages"][1]["references"] == [
        f"project:{project.project_id}",
        "decision:decision-abcdefabcdef",
    ]
    assert "批准" in result["messages"][1]["text"]
    assert len(service.messages(project.project_id, session_id)["messages"]) == 2


def test_session_intervention_forwards_repair_rejection(tmp_path, monkeypatch):
    runtime, project = _completed_runtime(tmp_path)
    service = ResearchSessionService(runtime)
    session_id = service.create(project.project_id, title="修复拒绝")["session"]["session_id"]

    captured = {}

    def fake_decide_repair(*, project_id, repair_request_id, trigger_snapshot_digest, approve, actor, rationale, resume=False):
        captured.update(
            project_id=project_id,
            repair_request_id=repair_request_id,
            trigger_snapshot_digest=trigger_snapshot_digest,
            approve=approve,
            actor=actor,
            rationale=rationale,
        )
        return {
            "decision": {
                "decision_id": "decision-repair-deadbeef",
                "action": "reject",
                "target_ids": [repair_request_id],
            },
            "project": {},
        }

    monkeypatch.setattr(service.projects_service, "decide_repair", fake_decide_repair)
    result = service.intervene(
        project.project_id,
        session_id,
        action="decide_repair",
        rationale="设计有误，拒绝该修复",
        actor="reviewer",
        target_id="repair-abcdefabcdef123456789012",
        approve=False,
        snapshot_digest="a" * 64,
    )
    assert captured["approve"] is False
    assert captured["trigger_snapshot_digest"] == "a" * 64
    assert "拒绝" in result["messages"][1]["text"]


def test_session_intervention_rejects_unsupported_or_incomplete_actions(tmp_path):
    runtime, project = _completed_runtime(tmp_path)
    service = ResearchSessionService(runtime)
    session_id = service.create(project.project_id, title="错误路径")["session"]["session_id"]

    with pytest.raises(ValueError, match="unsupported"):
        service.intervene(project.project_id, session_id, action="run_arbitrary_code", rationale="x")
    with pytest.raises(ValueError, match="target_id"):
        service.intervene(project.project_id, session_id, action="accept_checkpoint", rationale="x")
    with pytest.raises(ValueError, match="snapshot_digest"):
        service.intervene(
            project.project_id,
            session_id,
            action="decide_repair",
            rationale="x",
            target_id="repair-abcdefabcdef123456789012",
            approve=True,
        )
    assert service.messages(project.project_id, session_id)["messages"] == []


def test_session_intervention_web_endpoint_queues_resume(tmp_path, monkeypatch):
    from target_agent.research_session import ResearchSessionService

    research_runtime, _ = fake_research_runtime(tmp_path)
    client = create_app(
        fake_target_runtime(tmp_path),
        research_runtime=research_runtime,
    ).test_client()
    project = research_project("project-session-web")
    assert client.post("/api/projects", json=project.model_dump(mode="json")).status_code == 202
    _wait_for_project(client, project.project_id)
    session_id = client.post(
        f"/api/projects/{project.project_id}/sessions", json={"title": "干预"}
    ).get_json()["session"]["session_id"]

    calls = {}

    def fake_intervene(self, project_id, session_id, *, action, rationale, actor, target_id, approve, snapshot_digest, mode=None, rollback_to_attempt_id=None, input_overrides=None):
        calls.update(
            project_id=project_id,
            session_id=session_id,
            action=action,
            rationale=rationale,
            target_id=target_id,
        )
        return {
            "project_id": project_id,
            "session_id": session_id,
            "messages": [
                {
                    "message_id": "msg-user",
                    "role": "user",
                    "kind": "intervention",
                    "text": rationale,
                    "source_bound": False,
                },
                {
                    "message_id": "msg-result",
                    "role": "system",
                    "kind": "intervention_result",
                    "text": "已记录决策",
                    "references": [f"decision:{'decision-abcdefabcdef'}"],
                    "source_bound": False,
                },
            ],
            "decision": {
                "decision_id": "decision-abcdefabcdef",
                "action": "accept",
                "target_ids": [target_id],
            },
        }

    monkeypatch.setattr(ResearchSessionService, "intervene", fake_intervene)
    response = client.post(
        f"/api/projects/{project.project_id}/sessions/{session_id}/interventions",
        json={
            "action": "accept_checkpoint",
            "rationale": "会话中批准",
            "actor": "reviewer",
            "target_id": "plan-xyz",
        },
    )
    assert response.status_code == 202
    payload = response.get_json()
    assert payload["decision_persisted"] is True
    assert payload["resume_queued"] is True
    assert calls["action"] == "accept_checkpoint"
    assert payload["status_url"] == f"/api/projects/{project.project_id}"

def test_session_intervention_forwards_propose_fork_supplement(tmp_path, monkeypatch):
    runtime, project = _completed_runtime(tmp_path)
    service = ResearchSessionService(runtime)
    session_id = service.create(project.project_id, title="补充输入")["session"]["session_id"]

    captured = {}

    def fake_propose_fork(*, project_id, target_work_item_id, mode, rationale, actor, rollback_to_attempt_id, input_overrides):
        captured.update(
            project_id=project_id,
            target_work_item_id=target_work_item_id,
            mode=mode,
            rationale=rationale,
            actor=actor,
            rollback_to_attempt_id=rollback_to_attempt_id,
            input_overrides=input_overrides,
        )
        return {
            "state": {
                "status": "waiting_review",
                "checkpoint_kind": "fork",
                "checkpoint_target_id": "branch-abcdefabcdef123456",
                "current_item_id": target_work_item_id,
            }
        }

    monkeypatch.setattr(service.projects_service, "propose_fork", fake_propose_fork)
    result = service.intervene(
        project.project_id,
        session_id,
        action="propose_fork",
        rationale="补充目标组织为结肠",
        actor="researcher",
        target_id="target_discovery",
        input_overrides={"target_discovery": {"tissue": "colon"}},
    )
    assert captured == {
        "project_id": project.project_id,
        "target_work_item_id": "target_discovery",
        "mode": "redo",
        "rationale": "补充目标组织为结肠",
        "actor": "researcher",
        "rollback_to_attempt_id": None,
        "input_overrides": {"target_discovery": {"tissue": "colon"}},
    }
    assert result["fork"] == {
        "branch_id": "branch-abcdefabcdef123456",
        "mode": "redo",
        "target_work_item_id": "target_discovery",
        "status": "proposed",
    }
    assert [m["kind"] for m in result["messages"]] == ["intervention", "intervention_result"]
    assert "branch-abcdefabcdef123456" in result["messages"][1]["text"]
    assert result["messages"][1]["references"][-1] == "branch:branch-abcdefabcdef123456"


def test_session_intervention_rejects_bad_supplement_payloads(tmp_path):
    runtime, project = _completed_runtime(tmp_path)
    service = ResearchSessionService(runtime)
    session_id = service.create(project.project_id, title="错误补充")["session"]["session_id"]

    with pytest.raises(ValueError, match="target_id"):
        service.intervene(project.project_id, session_id, action="propose_fork", rationale="x")
    with pytest.raises(ValueError, match="mode"):
        service.intervene(
            project.project_id,
            session_id,
            action="propose_fork",
            rationale="x",
            target_id="target_discovery",
            mode="rewrite",
        )
    with pytest.raises(ValueError, match="input_overrides"):
        service.intervene(
            project.project_id,
            session_id,
            action="propose_fork",
            rationale="x",
            target_id="target_discovery",
            input_overrides=["not", "a", "dict"],
        )
    assert service.messages(project.project_id, session_id)["messages"] == []


def test_session_intervention_web_endpoint_propose_fork_no_resume(tmp_path, monkeypatch):
    from target_agent.research_session import ResearchSessionService

    research_runtime, _ = fake_research_runtime(tmp_path)
    client = create_app(
        fake_target_runtime(tmp_path),
        research_runtime=research_runtime,
    ).test_client()
    project = research_project("project-session-web")
    assert client.post("/api/projects", json=project.model_dump(mode="json")).status_code == 202
    _wait_for_project(client, project.project_id)
    session_id = client.post(
        f"/api/projects/{project.project_id}/sessions", json={"title": "补充输入"}
    ).get_json()["session"]["session_id"]

    calls = {}

    def fake_intervene(self, project_id, session_id, *, action, rationale, actor, target_id, approve, snapshot_digest, mode, rollback_to_attempt_id, input_overrides):
        calls.update(action=action, mode=mode, input_overrides=input_overrides)
        return {
            "project_id": project_id,
            "session_id": session_id,
            "messages": [
                {
                    "message_id": "msg-user",
                    "role": "user",
                    "kind": "intervention",
                    "text": rationale,
                    "source_bound": False,
                },
                {
                    "message_id": "msg-result",
                    "role": "system",
                    "kind": "intervention_result",
                    "text": "已发起补充输入回退",
                    "references": [f"branch:{'branch-abcdefabcdef123456'}"],
                    "source_bound": False,
                },
            ],
            "fork": {
                "branch_id": "branch-abcdefabcdef123456",
                "mode": mode,
                "target_work_item_id": target_id,
                "status": "proposed",
            },
        }

    monkeypatch.setattr(ResearchSessionService, "intervene", fake_intervene)
    response = client.post(
        f"/api/projects/{project.project_id}/sessions/{session_id}/interventions",
        json={
            "action": "propose_fork",
            "rationale": "补充目标组织",
            "actor": "researcher",
            "target_id": "target_discovery",
            "mode": "redo",
            "input_overrides": {"target_discovery": {"tissue": "colon"}},
        },
    )
    assert response.status_code == 202
    payload = response.get_json()
    assert payload["resume_queued"] is False
    assert payload["fork"]["branch_id"] == "branch-abcdefabcdef123456"
    assert calls == {
        "action": "propose_fork",
        "mode": "redo",
        "input_overrides": {"target_discovery": {"tissue": "colon"}},
    }