"""Gold-paper nomination tests: deterministic scoring, gap bias and store integrity."""
from __future__ import annotations

from pathlib import Path

import pytest

from target_agent.gold_nomination import (
    GoldNomination,
    load_nominations,
    nominate_candidates,
    render_nominations,
    write_nominations,
)
from target_agent.paper_corpus import PaperCandidate


def _candidate(
    pmid,
    title,
    *,
    journal="Nature",
    year=2024,
    buckets=None,
    status="candidate",
    exclusion_reason=None,
):
    return PaperCandidate(
        pmid=pmid,
        title=title,
        journal=journal,
        year=year,
        query_buckets=buckets or ["gwas_target"],
        status=status,
        exclusion_reason=exclusion_reason,
    )


def test_nomination_is_deterministic_and_ranked():
    weaker = _candidate("10000001", "Genetic association at a disease locus")
    stronger = _candidate(
        "10000002",
        "CRISPR screen identifies therapeutic targets in ulcerative colitis",
        buckets=["perturbation_screen"],
    )
    rows = nominate_candidates([weaker, stronger], limit=10)
    assert [row.pmid for row in rows] == ["10000002", "10000001"]
    assert rows[0].score > rows[1].score
    assert rows[0].signal_lanes == ["perturbation", "target_drug"]
    assert rows[0].gap_diseases == ["uc"]
    assert all(row.status == "nominated" and row.advisory for row in rows)
    assert all(row.digest == row.compute_digest() for row in rows)
    again = nominate_candidates([weaker, stronger], limit=10)
    assert [row.digest for row in rows] == [row.digest for row in again]


def test_eligibility_filters_status_year_and_score():
    rows = nominate_candidates([
        _candidate("10000003", "GWAS fine-mapping pinpoints a causal gene", year=2020),
        _candidate("10000004", "GWAS fine-mapping pinpoints a causal gene", status="excluded", exclusion_reason="excluded in test"),
        _candidate("10000005", "Single-cell atlas of tumour microenvironment"),
    ], limit=10, year_min=2021)
    assert [row.pmid for row in rows] == ["10000005"]
    rows_limited = nominate_candidates([
        _candidate("10000006", "GWAS fine-mapping pinpoints a causal gene"),
        _candidate("10000007", "CRISPR screen for drug targets"),
    ], limit=1)
    assert len(rows_limited) == 1


def test_min_score_filters_low_scoring_nominations():
    rows = nominate_candidates([
        _candidate("10000008", "GWAS fine-mapping pinpoints a causal gene"),
    ], limit=10, min_score=99.0)
    assert rows == []


def test_basic_biology_only_title_is_not_eligible():
    rows = nominate_candidates([
        _candidate("10000009", "Yeast cell cycle"),
    ], limit=10)
    assert rows == []


def test_gap_disease_bonus_is_recorded():
    rows = nominate_candidates([
        _candidate("10000010", "Psoriasis GWAS to drug target"),
    ], limit=10)
    assert rows
    assert rows[0].gap_diseases == ["psoriasis"]
    assert any("RAG gap disease" in reason for reason in rows[0].reasons)


def test_write_load_roundtrip_and_digest_guard(tmp_path):
    rows = nominate_candidates([
        _candidate("10000011", "CRISPR screen identifies therapeutic targets in ulcerative colitis"),
    ], limit=10)
    target = tmp_path / "nominations.jsonl"
    written = write_nominations(target, rows)
    assert written["nominations"] == 1
    assert (tmp_path / "nominations_MANIFEST.json").is_file()
    loaded = load_nominations(target)
    assert [row.digest for row in loaded] == [row.digest for row in rows]
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "digest" in lines[0]
    tampered = lines[0].replace("ulcerative colitis", "colitis")
    target.write_text(tampered + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_nominations(target)


def test_render_returns_jsonl():
    rows = nominate_candidates([
        _candidate("10000012", "Single-cell atlas of tumour microenvironment"),
    ], limit=10)
    rendered = render_nominations(rows)
    assert rendered.endswith("\n")
    assert rendered.count("\n") == 1
    assert GoldNomination.model_validate_json(rendered.strip()).pmid == "10000012"


def test_committed_corpus_yields_nomination_shortlist():
    corpus = Path(__file__).resolve().parents[1] / "paper_strategy" / "corpus" / "corpus.jsonl"
    assert corpus.is_file()
    from target_agent.paper_corpus import CorpusStore

    rows = nominate_candidates(CorpusStore(corpus).all(), limit=40)
    assert 20 <= len(rows) <= 40
    assert all(row.status == "nominated" and row.advisory for row in rows)
    assert all(row.reasons for row in rows)


def test_digest_mismatch_is_rejected_on_construct():
    row = _candidate("10000013", "GWAS fine-mapping pinpoints a causal gene")
    data = nominate_candidates([row], limit=10)[0].model_dump()
    data["digest"] = "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        GoldNomination.model_validate(data)
