"""Wiring tests for the LoRA reviewer backend.

Uses the local CPU smoke adapter (Qwen3-0.6B, 1 training step) to validate the
integration mechanics: probe construction, generation, JSON extraction,
category cross-check and ReviewerFinding mapping. Output *quality* is covered
by the heldout evaluation of the full 8B adapter, not here.
"""
import json
import sys
from pathlib import Path

import pytest

from target_agent.contracts import (
    ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, ReviewerFinding,
    SourceLocator, Stance, TaskConstraints, TaskContext, TaskSpec, ToolCapability,
    ToolResult, ToolStatus, new_id,
)
from target_agent.reviewer import Reviewer
from target_agent.reviewer_lora import CATEGORIES, LoRAReviewerBackend, build_probes, extract_json
from target_agent.settings import Settings

ROOT = Path(__file__).resolve().parents[1]
SMOKE_BASE = ROOT / "models" / "qwen3-0.6b"
SMOKE_ADAPTER = ROOT / "models" / "reviewer-lora-smoke"
needs_smoke = pytest.mark.skipif(
    not (SMOKE_BASE.exists() and SMOKE_ADAPTER.exists()),
    reason="local smoke model/adapter not present",
)


def uc_task_missing_context():
    return TaskSpec(task_type="disease_to_target", question="Prioritize UC targets",
                    context=TaskContext(disease="ulcerative colitis"))  # no tissue/cell_type


def failed_result():
    return ToolResult(
        tool_name="open_targets", tool_version="test", status=ToolStatus.FAILED,
        coverage_status=CoverageStatus.NOT_COVERED, context_match_score=0.0,
        error="simulated timeout", inputs={}, outputs={},
        capability=ToolCapability(validation_scope="test"), candidate_genes=[],
    )


def causal_evidence(tool_run_id: str):
    return EvidenceItem(
        tool_run_id=tool_run_id, gene_symbol="IL12B", claim_class=ClaimClass.OBSERVED,
        statement="IL12B drives disease progression in UC.",
        source=SourceLocator(uri="https://example.org/x", source_id="x", chunk_id="x-1"),
        source_span="span", context=EvidenceContext(disease="ulcerative colitis"),
        stance=Stance.SUPPORTS, uncertainty="u", quality_flags=[], context_match_score=1.0,
    )


def test_probe_construction_covers_case_conditions():
    task = uc_task_missing_context()
    result = failed_result()
    evidence = [causal_evidence(result.tool_run_id)]
    probes = build_probes(task, [result], evidence)
    categories = {p["category"] for p in probes}
    assert {"missing_context", "tool_failure", "causal_overreach"} <= categories
    assert all(p["related_ids"] for p in probes)


def test_extract_json_tolerates_chatter():
    assert extract_json('noise {"severity": "major", "category": "tool_failure", "action": "x"} tail')["severity"] == "major"
    assert extract_json("plain text") is None


def test_reviewer_without_lora_settings_keeps_deterministic_backend():
    reviewer = Reviewer(None)
    findings = reviewer.review(uc_task_missing_context(), [], [])
    assert isinstance(findings, list)
    assert reviewer.last_backend == "deterministic"


def test_reviewer_ignores_incomplete_lora_configuration():
    settings = Settings(TARGET_AGENT_REVIEWER_LORA_ADAPTER=str(SMOKE_ADAPTER))
    reviewer = Reviewer(None, settings=settings)
    assert reviewer._lora is None


def test_failed_lora_falls_back_to_step(monkeypatch):
    class FakeStepClient:
        model = "fake"

        def __init__(self):
            self.called = False

        def json_completion(self, system, payload, **kwargs):
            self.called = True
            return {"findings": []}

    settings = Settings(
        TARGET_AGENT_REVIEWER_LORA_BASE=str(SMOKE_BASE),
        TARGET_AGENT_REVIEWER_LORA_ADAPTER=str(SMOKE_ADAPTER),
    )
    client = FakeStepClient()
    reviewer = Reviewer(client, settings=settings)
    monkeypatch.setattr(
        reviewer._lora,
        "findings",
        lambda *args: (_ for _ in ()).throw(RuntimeError("simulated adapter failure")),
    )
    reviewer.review(uc_task_missing_context(), [], [])
    assert client.called is True
    assert reviewer.last_backend == "step:fake"


@needs_smoke
def test_lora_backend_generates_valid_findings_only(tmp_path):
    backend = LoRAReviewerBackend(SMOKE_BASE, SMOKE_ADAPTER, max_new_tokens=96)
    task = uc_task_missing_context()
    result = failed_result()
    findings = backend.findings(task, [result], [causal_evidence(result.tool_run_id)])
    allowed = {task.task_id, result.tool_run_id, "x-ev"}
    canonical = {"missing_provenance", "context_mismatch", "causal_overreach", "conflicting_evidence",
                 "numeric_error", "coverage_gap", "tool_failure", "dataset_ineligibility"}
    for finding in findings:
        assert isinstance(finding, ReviewerFinding)
        assert finding.category in canonical  # SFT categories are mapped to the public contract
        assert finding.severity in {"blocking", "major", "minor"}
        assert finding.required_action.strip()


def test_sft_categories_map_to_canonical_finding_categories(monkeypatch):
    """Confirmed SFT-only categories (e.g. missing_context) must become valid ReviewerFindings."""
    backend = LoRAReviewerBackend(SMOKE_BASE, SMOKE_ADAPTER)
    monkeypatch.setattr(backend, "_load", lambda: None)
    monkeypatch.setattr(backend, "_answer", lambda instruction, payload: {
        "severity": "major", "category": "missing_context",
        "action": "ask for tissue and cell type before ranking"})
    findings = backend.findings(uc_task_missing_context(), [], [])
    assert len(findings) == 1
    assert findings[0].category == "coverage_gap"
    assert findings[0].severity == "major"
    assert "missing_context" in findings[0].message


@needs_smoke
def test_reviewer_uses_lora_backend_when_configured():
    settings = Settings(TARGET_AGENT_REVIEWER_LORA_BASE=str(SMOKE_BASE),
                        TARGET_AGENT_REVIEWER_LORA_ADAPTER=str(SMOKE_ADAPTER))
    reviewer = Reviewer(None, settings=settings)
    assert reviewer._lora is not None
    result = failed_result()
    findings = reviewer.review(uc_task_missing_context(), [result], [])
    # deterministic gates still fire independently of adapter output quality
    assert any(f.category == "tool_failure" and f.severity == "major" for f in findings)
    assert reviewer.last_backend in {"lora:reviewer-lora-smoke", "deterministic:lora_unavailable"}

def test_reviewer_llm_findings_reuse_persistent_cache(tmp_path):
    class FakeStepClient:
        model = "fake"

        def __init__(self):
            self.calls = 0

        def json_completion(self, system, payload, **kwargs):
            self.calls += 1
            return {"findings": [{
                "severity": "major", "category": "context_mismatch",
                "message": "cached review finding", "related_ids": [],
                "required_action": "check",
            }]}

    client = FakeStepClient()
    reviewer = Reviewer(client, cache_dir=tmp_path / "cache")
    first = reviewer.review(uc_task_missing_context(), [], [])
    assert client.calls == 1
    assert reviewer.last_backend == "step:fake"
    second = reviewer.review(uc_task_missing_context(), [], [])
    assert client.calls == 1
    assert reviewer.last_backend == "step:fake:cached"
    assert [f.message for f in first] == [f.message for f in second]
    assert (tmp_path / "cache" / "reviewer_llm").is_dir()
