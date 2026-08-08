from __future__ import annotations

from target_agent.research_planner import ResearchPlanner
from target_agent.settings import PROJECT_ROOT
from target_agent.skill_catalog import SkillCatalog, SkillHintBuilder

from .test_research_runtime import fake_research_runtime, research_project


def _catalog() -> SkillCatalog:
    return SkillCatalog(PROJECT_ROOT / "skills")


def test_catalog_loads_all_curated_skills_with_stable_checksums():
    catalog = _catalog()
    skills = catalog.list_skills()
    assert len(skills) >= 6
    ids = [skill.skill_id for skill in skills]
    assert len(ids) == len(set(ids))
    for skill in skills:
        assert skill.path.endswith("SKILL.md")
        assert len(skill.sha256) == 64
        assert skill.description
        assert skill.char_count > 0
    again = _catalog()
    assert [skill.sha256 for skill in skills] == [skill.sha256 for skill in again.list_skills()]


def test_search_respects_lane_and_scope_filters():
    catalog = _catalog()
    hits = catalog.search(lanes=["literature"], scopes=["disease_target_discovery"], top_k=5)
    assert hits
    assert any(hit.skill.skill_id == "literature-evidence-extraction" for hit in hits)
    assert all("literature" in hit.skill.evidence_lanes for hit in hits)
    query_hits = catalog.search(query="pseudobulk", top_k=3)
    assert query_hits
    assert query_hits[0].skill.skill_id == "single-cell-pseudobulk"


def test_load_returns_full_body_on_demand_and_unknown_is_none():
    catalog = _catalog()
    loaded = catalog.load("target-card-review")
    assert loaded is not None
    assert "GO" in loaded["content"]
    assert catalog.get("missing-skill") is None


def test_hint_builder_returns_compact_blocks_without_full_content():
    catalog = _catalog()
    builder = SkillHintBuilder(catalog, top_k=2)
    hints = builder.build(lanes=["genetics"], scopes=["disease_target_discovery"])
    assert 1 <= len(hints) <= 2
    for hint in hints:
        assert "content" not in hint
        assert hint["id"] and hint["description"] and hint["evidence_lanes"]


def test_runtime_exposes_skill_catalog_and_workflow_unchanged(tmp_path):
    runtime, _ = fake_research_runtime(tmp_path)
    assert runtime.skill_catalog.count >= 6
    planner = ResearchPlanner(
        runtime.registry,
        client=None,
        skill_catalog=runtime.skill_catalog,
        skill_hint_top_k=2,
    )
    plan = planner.deterministic(research_project(
        "project-planner-skills",
        domain="disease_target_discovery",
        context={"target_task_spec": {"task_type": "disease_to_target", "question": "Find targets", "context": {"disease": "asthma"}}},
    ))
    assert plan.planner_backend.startswith("deterministic")
    assert "target_discovery" in {item.module for item in plan.items}
    hints = planner.skill_hints.build(lanes=["literature"], scopes=["disease_target_discovery"])
    assert hints


def test_web_skills_endpoints(tmp_path):
    from target_agent.webapp import create_app

    from .test_runtime import fake_runtime as fake_target_runtime

    app = create_app(fake_target_runtime(tmp_path))
    client = app.test_client()
    caps = client.get("/api/capabilities").get_json()
    assert caps["skills"]["count"] >= 6
    listing = client.get("/api/skills").get_json()
    assert listing["count"] == caps["skills"]["count"]
    detail = client.get("/api/skills/literature-evidence-extraction")
    assert detail.status_code == 200
    assert "content" in detail.get_json()
    assert client.get("/api/skills/not-a-skill").status_code == 404
