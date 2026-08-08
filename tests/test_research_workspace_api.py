from __future__ import annotations

import io
import zipfile

import pytest

from target_agent.research_service import ResearchProjectService
from target_agent.research_store import ResearchProjectStore

from .test_research_runtime import fake_research_runtime, research_project


def _completed_project(tmp_path, project_id: str = "project-workspace"):
    runtime, _ = fake_research_runtime(tmp_path)
    project = research_project(project_id)
    runtime.run(project)
    service = ResearchProjectService(runtime)
    return runtime, project, service


def test_evidence_graph_contains_work_items_artifacts_and_edges(tmp_path):
    _, project, service = _completed_project(tmp_path)
    graph = service.evidence_graph(project.project_id)
    node_ids = {node["id"] for node in graph["nodes"]}
    assert any(node["kind"] == "work_item" for node in graph["nodes"])
    assert any(node["kind"] == "artifact" for node in graph["nodes"])
    kinds = {edge["kind"] for edge in graph["edges"]}
    assert "depends_on" in kinds
    assert "produces" in kinds
    for edge in graph["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
    work_items = [node for node in graph["nodes"] if node["kind"] == "work_item"]
    assert all(node["status"] in {"completed", "completed_with_gaps", "pending", "running", "failed", "blocked"} for node in work_items)


def test_project_files_excludes_secret_like_names(tmp_path):
    runtime, project, service = _completed_project(tmp_path, "project-files")
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    store.project_dir.joinpath(".env").write_text("STEP_API_KEY=top-secret\n", encoding="utf-8")
    page = service.project_files(project.project_id)
    paths = [row["path"] for row in page["files"]]
    assert ".env" not in paths
    report = next(row for row in store.read_artifacts() if row.logical_name == "research_report")
    report_rel = store.artifact_path(report).relative_to(store.project_dir).as_posix()
    assert report_rel in paths


def test_preview_file_returns_text_and_rejects_escape(tmp_path):
    runtime, project, service = _completed_project(tmp_path, "project-preview")
    store = ResearchProjectStore(runtime.projects_dir, project.project_id)
    report = next(row for row in store.read_artifacts() if row.logical_name == "research_report")
    report_rel = store.artifact_path(report).relative_to(store.project_dir).as_posix()
    preview = service.preview_file(project.project_id, report_rel)
    assert preview["content"].startswith("# Fake research report")
    assert preview["truncated"] is False
    with pytest.raises(ValueError, match="escapes the project directory"):
        service.preview_file(project.project_id, "../project_spec.json")
    with pytest.raises(ValueError, match="secret-like"):
        service.preview_file(project.project_id, ".env")


def test_workspace_web_endpoints_serve_graph_files_and_preview(tmp_path):
    from target_agent.webapp import create_app

    from .test_research_web_api import _wait_for_project
    from .test_runtime import fake_runtime as fake_target_runtime

    research_runtime, _ = fake_research_runtime(tmp_path)
    app = create_app(fake_target_runtime(tmp_path), research_runtime=research_runtime)
    client = app.test_client()
    project = research_project("project-web-workspace")
    created = client.post("/api/projects", json=project.model_dump(mode="json"))
    assert created.status_code == 202
    _wait_for_project(client, project.project_id)

    graph = client.get(f"/api/projects/{project.project_id}/graph")
    assert graph.status_code == 200
    assert graph.get_json()["nodes"]
    assert graph.get_json()["edges"]

    files = client.get(f"/api/projects/{project.project_id}/files")
    assert files.status_code == 200
    rows = files.get_json()["files"]
    assert rows
    report_path = next(row["path"] for row in rows if row["path"].endswith(".md"))

    preview = client.get(
        f"/api/projects/{project.project_id}/files/preview?path={report_path}"
    )
    assert preview.status_code == 200
    assert preview.get_json()["content"].startswith("# Fake research report")

    escape = client.get(
        f"/api/projects/{project.project_id}/files/preview?path=..%2Fproject_spec.json"
    )
    assert escape.status_code == 400
