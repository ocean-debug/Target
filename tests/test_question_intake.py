"""Question intake tests: deterministic gates, LLM fallback and draft integrity."""
from __future__ import annotations

import json

import pytest

from target_agent.diseases import load_library
from target_agent.llm import LLMUnavailable
from target_agent.question_intake import (
    QuestionNeedsInput,
    _detect_disease,
    build_draft,
)
from target_agent.research_contracts import ResearchProjectSpec


class _FakeClient:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def json_completion(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.payload


def test_detects_curated_disease_from_free_text():
    hit = _detect_disease(
        "Which drug targets are supported by public evidence for ulcerative colitis?",
        load_library(),
    )
    assert hit is not None
    entry, _ = hit
    assert entry.name == "ulcerative colitis"
    assert entry.ontology_id == "MONDO:0005101"


def test_draft_without_llm_uses_library_match_and_never_injects_context():
    draft = build_draft(
        "Which mechanisms and drug targets are supported by public evidence for ulcerative colitis?",
        client=None,
    )
    assert draft.disease_resolution["matched"] is True
    assert draft.disease_resolution["canonical_name"] == "ulcerative colitis"
    assert draft.disease_resolution["ontology_id"] == "MONDO:0005101"
    assert draft.extracted["disease"] == "ulcerative colitis"
    assert draft.extracted["tissue"] is None
    assert draft.needs_review is True
    assert any("library_context_suggestion" in note for note in draft.review_notes)
    spec = ResearchProjectSpec.model_validate(draft.spec)
    assert spec.goal.question == draft.question
    assert spec.context["target_task_spec"]["context"]["tissue"] is None


def test_hints_override_free_text_detection():
    draft = build_draft(
        "Which mechanisms and drug targets are supported by public evidence for ulcerative colitis?",
        hints={"disease": "Crohn disease"},
        client=None,
    )
    assert draft.extracted["disease"] == "Crohn disease"
    assert draft.disease_resolution["canonical_name"] == "Crohn disease"
    assert draft.sources["disease"] == "user"


def test_llm_fields_accepted_and_rewrite_applied():
    fake = _FakeClient(payload={
        "question_rewrite": "Which colon-localized mechanisms and drug targets have public evidence in ulcerative colitis?",
        "disease": "ulcerative colitis",
        "tissue": "colon",
        "desired_phenotype": "restore mucosal homeostasis",
        "field_confidence": {"disease": "high", "tissue": "high", "desired_phenotype": "medium"},
    })
    question = "What are the targets in ulcerative colitis?"
    draft = build_draft(question, client=fake)
    assert draft.extracted["tissue"] == "colon"
    assert draft.sources["tissue"] == "llm"
    spec = ResearchProjectSpec.model_validate(draft.spec)
    assert spec.goal.question.startswith("Which colon-localized")
    assert spec.context["original_question"] == question
    assert fake.calls


def test_llm_unavailable_falls_back_to_deterministic():
    fake = _FakeClient(error=LLMUnavailable("down"))
    draft = build_draft(
        "Which mechanisms and drug targets are supported by public evidence for ulcerative colitis?",
        client=fake,
    )
    assert draft.disease_resolution["matched"] is True
    assert any("llm_unavailable" in note for note in draft.review_notes)


def test_missing_disease_requires_input():
    with pytest.raises(QuestionNeedsInput, match="no disease could be established"):
        build_draft("Which mechanisms explain therapy resistance?", client=None)


def test_credential_like_token_is_rejected():
    with pytest.raises(QuestionNeedsInput, match="credential-like"):
        build_draft("Targets for disease " + "sk-" + "a" * 30, client=None)


def test_short_question_is_rejected():
    with pytest.raises(QuestionNeedsInput, match="at least 3"):
        build_draft("hi", client=None)


def test_web_question_endpoint_returns_draft_without_creating(tmp_path):
    from target_agent.webapp import create_app

    app = create_app()
    client = app.test_client()
    response = client.post("/api/questions", json={
        "question": "Which mechanisms and drug targets are supported by public evidence for ulcerative colitis?",
    })
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["disease_resolution"]["matched"] is True
    assert payload["needs_review"] is True
    assert ResearchProjectSpec.model_validate(payload["spec"]).goal.question
    missing = client.post("/api/questions", json={})
    assert missing.status_code == 400
    no_disease = client.post("/api/questions", json={"question": "Which mechanisms explain resistance?"})
    assert no_disease.status_code == 422


def test_ask_cli_prints_draft_without_reserving(monkeypatch, capsys, tmp_path):
    import sys

    from target_agent import cli

    monkeypatch.setattr(sys, "argv", [
        "target-agent", "ask",
        "--question", "Which mechanisms and drug targets are supported by public evidence for ulcerative colitis?",
        "--disease", "ulcerative colitis",
        "--output", str(tmp_path / "draft.yaml"),
    ])
    cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["disease_resolution"]["matched"] is True
    assert payload.get("created") is not True
    assert (tmp_path / "draft.yaml").is_file()
