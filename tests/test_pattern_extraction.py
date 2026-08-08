"""Curation, extraction, audit and review-ledger tests.

All tests use injected fakes; no network and no real LLM calls.
"""
from __future__ import annotations

import json

import pytest

from target_agent.paper_corpus import PaperCandidate
from target_agent.paper_strategy import (
    PatternStore, ReviewEntry, ReviewLedger, StrategyPattern,
)
from target_agent.pattern_extraction import (
    CurationRecord, CurationStore, ExtractionAuditRecord, ExtractionAuditStore,
    ExtractionResult, PaperMeta, PatternExtractor, run_extraction,
)


def _paper(pmid: str = "35860525") -> PaperCandidate:
    return PaperCandidate(
        pmid=pmid, title="GWAS identifies a causal target for colitis",
        journal="Nature", year=2022, query_buckets=["gwas_target"],
        status="candidate",
    )


def _meta(pmid: str = "35860525") -> PaperMeta:
    return PaperMeta(
        pmid=pmid, title="GWAS identifies a causal target for colitis",
        journal="Nature", year=2022, doi="10.1038/example",
        pmcid="PMC123456", source_text="GWAS fine-mapping and eQTL analysis...",
        source_material="abstract",
    )


def _valid_payload(pmid: str) -> dict:
    return {
        "name": "Genetics-first colitis pattern",
        "disease_class": "ulcerative colitis",
        "disease_keywords": ["colitis", "ibd"],
        "applicability": ["GWAS summary statistics available"],
        "evidence_start_lane": "genetics",
        "ordered_lanes": ["genetics", "omics", "literature"],
        "required_lanes": ["genetics", "omics"],
        "optional_lanes": ["literature"],
        "evidence_links": [{
            "link_id": "link-1", "source_lane": "genetics", "target_lane": "omics",
            "link_type": "gwas_to_eqtl", "evidence_used": ["eQTL"],
            "decision_rule": "coloc PP4 >= 0.8", "why_this_link": "anchor variant to gene",
        }],
        "stop_downgrade_rules": ["Do not promote variant-only hits"],
        "mixed_method_rationale": "GWAS power first, then eQTL anchor.",
        "boundary_notes": ["Pattern is a strategy hint, not evidence."],
        "observed_workflows": [{
            "workflow_id": f"wf-{pmid}",
            "paper_title": "GWAS identifies a causal target for colitis",
            "journal": "Nature", "year": 2022, "disease": "ulcerative colitis",
            "data_availability": [{
                "lane": "genetics", "available": True, "source": "GWAS", "notes": "",
            }],
            "steps": [{
                "operation": "fine-map GWAS loci", "tool_abstraction": "fine_mapping",
                "input_lanes": ["genetics"], "output_lanes": ["genetics"],
                "decision_gate": "PP4 threshold", "why_this_step": "prioritize variants",
            }],
            "rationale": "genetics first",
        }],
    }


class FakeBackend:
    def __init__(self, payload: dict | None = None, error: Exception | None = None):
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def json_completion(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        if self.error is not None:
            raise self.error
        return json.loads(json.dumps(self.payload)) if self.payload else {}


class FakeMetaFetcher:
    def __init__(self, meta: PaperMeta | None = None):
        self.meta = meta
        self.calls: list[str] = []

    def fetch(self, pmid: str) -> PaperMeta | None:
        self.calls.append(pmid)
        return self.meta


def test_curation_store_append_only_and_latest_status(tmp_path):
    store = CurationStore(tmp_path / "curation.jsonl")
    first = CurationRecord(pmid="35860525", status="gold", rationale="GWAS + eQTL", annotator_role="life_science")
    assert store.add(first)
    assert not store.add(first)
    assert store.latest_status("35860525") == "gold"
    store.add(CurationRecord(pmid="35860525", status="rejected", rationale="insufficient methods", annotator_role="engineering"))
    assert store.latest_status("35860525") == "rejected"
    assert store.gold_pmids() == []
    assert store.card()["entries"] == 2


def test_extractor_adds_validated_pattern(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    extractor = PatternExtractor(
        backend=FakeBackend(payload=_valid_payload()),
        meta_fetcher=FakeMetaFetcher(meta=_meta()),
        pattern_store=store,
    )
    result = extractor.extract(_paper())
    assert result.pattern is not None
    assert result.pattern.pattern_id == "pattern-35860525"
    assert result.pattern.digest == result.pattern.compute_digest()
    assert result.pattern.source_papers[0].pmcid == "PMC123456"
    assert len(result.pattern.observed_workflows) == 1
    assert store.get("pattern-35860525") is not None
    # second extraction of the same paper is refused by the append-only store
    duplicate = extractor.extract(_paper())
    assert duplicate.pattern is None
    assert "already exists" in duplicate.error


def test_extractor_rejects_non_candidate_and_missing_meta(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    extractor = PatternExtractor(
        backend=FakeBackend(payload=_valid_payload()),
        meta_fetcher=FakeMetaFetcher(meta=None),
        pattern_store=store,
    )
    excluded = PaperCandidate(
        pmid="123", title="A review", journal="Nature", year=2022,
        query_buckets=["gwas_target"], status="excluded", exclusion_reason="review",
    )
    assert "only candidate" in extractor.extract(excluded).error
    assert "no public metadata" in extractor.extract(_paper("999")).error


def test_extractor_surfaces_schema_errors(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    payload = _valid_payload()
    payload["stop_downgrade_rules"] = []
    extractor = PatternExtractor(
        backend=FakeBackend(payload=payload),
        meta_fetcher=FakeMetaFetcher(meta=_meta()),
        pattern_store=store,
    )
    result = extractor.extract(_paper())
    assert result.pattern is None
    assert "schema validation" in result.error


def test_run_extraction_writes_audit(tmp_path):
    store = PatternStore(tmp_path / "patterns.jsonl")
    audit = ExtractionAuditStore(tmp_path / "extractions.jsonl")
    extractor = PatternExtractor(
        backend=FakeBackend(payload=_valid_payload()),
        meta_fetcher=FakeMetaFetcher(meta=_meta()),
        pattern_store=store,
    )
    outcome = run_extraction(papers=[_paper()], pattern_store=store, extractor=extractor, audit_store=audit)
    assert outcome["added"] == 1
    assert outcome["failed"] == 0
    assert audit.card()["added"] == 1
    assert audit.card()["entries"] == 1


def test_review_ledger_effective_gate(tmp_path):
    ledger = ReviewLedger(tmp_path / "reviews.jsonl")
    pattern = store_pattern()
    assert ledger.pending_count([pattern]) == 1
    ledger.add(ReviewEntry(pattern_id=pattern.pattern_id, role="life_science", status="approved"))
    gate = ledger.effective_gate(pattern)
    assert gate.life_science_review == "approved"
    assert gate.engineering_review == "pending"
    ledger.add(ReviewEntry(pattern_id=pattern.pattern_id, role="engineering", status="approved"))
    assert ledger.pending_count([pattern]) == 0
    ledger.add(ReviewEntry(pattern_id=pattern.pattern_id, role="engineering", status="rejected"))
    assert ledger.pending_count([pattern]) == 1


def store_pattern() -> StrategyPattern:
    payload = _valid_payload("12345678")
    payload["pattern_id"] = "pattern-12345678"
    return StrategyPattern.model_validate(payload)


__all__ = []
