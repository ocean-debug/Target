from __future__ import annotations

import time
from collections import Counter

from target_agent.project_package import import_project, inspect_package
from target_agent.research_contracts import AutonomyMode
from target_agent.research_store import ResearchProjectStore
from target_agent.webapp import create_app

from .test_research_runtime import BASELINE_MODULES, fake_research_runtime, research_project
from .test_runtime import fake_runtime as fake_target_runtime


def _wait_for(client, project_id, predicate, timeout_seconds: float = 10.0):
    deadline = time.monotonic() + timeout_seconds
    latest = None
    while time.monotonic() < deadline:
        latest = client.get(f"/api/projects/{project_id}").get_json()
        if predicate(latest):
            return latest
        time.sleep(0.01)
    raise AssertionError(
        f"project {project_id} did not satisfy predicate; last snapshot: {latest}"
    )


def test_product_journey_end_to_end_via_sessions_and_package(tmp_path):
    research_runtime, calls = fake_research_runtime(tmp_path)
    client = create_app(
        fake_target_runtime(tmp_path),
        research_runtime=research_runtime,
    ).test_client()
    project = research_project(
        "project-product-journey",
        autonomy_mode=AutonomyMode.CHECKPOINTED,
    )

    # 1. 提出问题，创建项目
    created = client.post("/api/projects", json=project.model_dump(mode="json"))
    assert created.status_code == 202
    project_id = project.project_id

    # 2. 等待计划检查点，并通过会话批准计划
    def at_plan(snap):
        return (snap.get("state") or {}).get("checkpoint_kind") == "plan"

    planned = _wait_for(client, project_id, at_plan)
    plan_target = planned["next_actions"][0]["target_id"]

    session_id = client.post(
        f"/api/projects/{project_id}/sessions", json={"title": "产品旅程"}
    ).get_json()["session"]["session_id"]
    approved = client.post(
        f"/api/projects/{project_id}/sessions/{session_id}/interventions",
        json={
            "action": "accept_checkpoint",
            "rationale": "计划范围与证据预算可接受",
            "actor": "reviewer",
            "target_id": plan_target,
        },
    )
    assert approved.status_code == 202
    assert approved.get_json()["resume_queued"] is True
    assert [m["kind"] for m in approved.get_json()["messages"]] == [
        "intervention", "intervention_result",
    ]

    # 3. 等待发布检查点，并通过会话批准发布
    def at_release(snap):
        return (snap.get("state") or {}).get("checkpoint_kind") == "release"

    release = _wait_for(client, project_id, at_release)
    release_target = release["next_actions"][0]["target_id"]
    released = client.post(
        f"/api/projects/{project_id}/sessions/{session_id}/interventions",
        json={
            "action": "accept_checkpoint",
            "rationale": "产物与报告通过审查",
            "actor": "reviewer",
            "target_id": release_target,
        },
    )
    assert released.status_code == 202

    # 4. 完成：所有必需工作项执行一次，报告产物存在
    def at_completed(snap):
        return (snap.get("state") or {}).get("status") == "completed"

    completed = _wait_for(client, project_id, at_completed)
    assert calls == Counter({name: 1 for name in BASELINE_MODULES})
    assert any(row["logical_name"] == "research_report" for row in completed["artifacts"])

    # 5. 会话内询问 Agent，得到确定性快照摘要（source_bound=false）
    asked = client.post(
        f"/api/projects/{project_id}/sessions/{session_id}/messages",
        json={"text": "现在到哪一步了？", "ask_agent": True, "actor": "researcher"},
    )
    assert asked.status_code == 200
    assert [m["role"] for m in asked.get_json()["messages"]] == ["user", "assistant"]
    assert asked.get_json()["messages"][1]["source_bound"] is False
    assert "当前状态" in asked.get_json()["messages"][1]["text"]

    # 6. 导出只读分享包：Web 字节流 -> inspect 校验 -> 导入第二目录
    exported = client.get(f"/api/projects/{project_id}/export")
    assert exported.status_code == 200
    package = tmp_path / "journey-package.zip"
    package.write_bytes(exported.data)
    metadata = inspect_package(package)
    assert metadata["project_id"] == project_id
    assert metadata["checksums_valid"] is True

    second_root = tmp_path / "projects-imported"
    imported = import_project(second_root, package)
    assert imported["imported"] is True
    imported_store = ResearchProjectStore(second_root, project_id)
    assert imported_store.load_state().status.value == "completed"

    original_store = ResearchProjectStore(research_runtime.projects_dir, project_id)
    original_report = next(
        row for row in original_store.read_artifacts()
        if row.logical_name == "research_report"
    )
    imported_report = next(
        row for row in imported_store.read_artifacts()
        if row.logical_name == "research_report"
    )
    assert imported_store.artifact_path(imported_report).read_text(encoding="utf-8") == (
        original_store.artifact_path(original_report).read_text(encoding="utf-8")
    )
    imported_store.assert_integrity()