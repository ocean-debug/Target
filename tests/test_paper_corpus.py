"""Candidate corpus pipeline: E-utilities parsing, deterministic filtering and
append-only store semantics. All tests use an injected fake transport; no
network access.
"""
from __future__ import annotations

import json

import pytest

from target_agent.paper_corpus import (
    CorpusStore, PaperCandidate, QUERY_BUCKETS, fetch_candidates, _normalize_journal,
)


def _row(pmid: str, title: str, journal: str, pubdate: str,
         doi: str | None = None, pmc: str | None = None) -> dict:
    article_ids = []
    if doi:
        article_ids.append({"idtype": "doi", "value": doi})
    if pmc:
        article_ids.append({"idtype": "pmc", "value": pmc})
    return {
        "uid": pmid,
        "title": title,
        "fulljournalname": journal,
        "pubdate": pubdate,
        "articleids": article_ids,
    }


class FakeEutils:
    def __init__(self, found: dict[tuple[str, str], list[str]],
                 summaries: dict[str, dict]):
        self.found = found
        self.summaries = summaries
        self.search_calls: list[tuple[str, str]] = []
        self.summary_calls: list[list[str]] = []

    def search(self, bucket_id, terms, journal, year_min, year_max, retmax):
        self.search_calls.append((bucket_id, journal))
        return self.found.get((bucket_id, journal), [])

    def summary(self, pmids):
        self.summary_calls.append(list(pmids))
        return {pmid: self.summaries[pmid] for pmid in pmids if pmid in self.summaries}


def test_fetch_filters_journal_year_and_title():
    client = FakeEutils(
        found={("gwas_target", "nature"): ["1", "2", "3", "4"]},
        summaries={
            "1": _row("1", "GWAS identifies a causal target for colitis", "Nature", "2022 Jan"),
            "2": _row("2", "A cross-sectional association study", "PLOS ONE", "2022 Mar"),
            "3": _row("3", "Old cohort mechanism study", "Nature", "2019 Jun"),
            "4": _row("4", "A systematic review of drug targets", "Nature", "2023 Feb"),
        },
    )

    records = fetch_candidates(client, year_min=2021, year_max=2026)

    by_pmid = {row.pmid: row for row in records}
    assert by_pmid["1"].status == "candidate"
    assert by_pmid["1"].exclusion_reason is None
    assert by_pmid["2"].status == "excluded"
    assert "journal not in whitelist" in by_pmid["2"].exclusion_reason
    assert by_pmid["3"].status == "excluded"
    assert "publication year" in by_pmid["3"].exclusion_reason
    assert by_pmid["4"].status == "excluded"
    assert "review/methods-only" in by_pmid["4"].exclusion_reason
    # candidates first (year desc, pmid asc), then excluded records
    assert [row.status for row in records] == ["candidate", "excluded", "excluded", "excluded"]
    assert by_pmid["1"].doi is None and by_pmid["1"].pmcid is None


def test_journal_normalization_accepts_parenthical_ncbi_names():
    assert _normalize_journal("Science (New York, N.Y.)") == "science"
    assert _normalize_journal("Nature Genetics") == "nature genetics"
    assert _normalize_journal("") == ""
    client = FakeEutils(
        found={("gwas_target", "science"): ["7"]},
        summaries={"7": _row("7", "Causal dissection of disease by genetics", "Science (New York, N.Y.)", "2023 May")},
    )
    records = fetch_candidates(client, year_min=2021, year_max=2026)
    assert records[0].status == "candidate"
    assert records[0].journal.startswith("Science")


def test_fetch_merges_query_buckets_and_article_ids():
    client = FakeEutils(
        found={
            ("gwas_target", "nature"): ["9"],
            ("single_cell_mechanism", "science"): ["9", "8"],
        },
        summaries={
            "9": _row("9", "Genetics and single-cell dissection of disease", "Science",
                      "2023 Apr", doi="10.1126/science.abc", pmc="PMC123"),
            "8": _row("8", "Cell atlas in disease", "Science", "2024 Jan"),
        },
    )

    records = fetch_candidates(client, year_min=2021, year_max=2026)

    assert len(records) == 2
    nine = next(row for row in records if row.pmid == "9")
    assert nine.query_buckets == ["gwas_target", "single_cell_mechanism"]
    assert nine.doi == "10.1126/science.abc"
    assert nine.pmcid == "PMC123"
    assert next(row for row in records if row.pmid == "8").query_buckets == ["single_cell_mechanism"]
    # every whitelisted journal is queried for every bucket
    assert len(client.search_calls) == len(QUERY_BUCKETS) * 10
    assert len(client.summary_calls) == 1


def test_fetch_caps_candidates_but_keeps_excluded_records():
    client = FakeEutils(
        found={("gwas_target", "nature"): ["1", "2", "3"]},
        summaries={
            "1": _row("1", "First candidate study", "Nature", "2022 Jan"),
            "2": _row("2", "Second candidate study", "Nature", "2023 Jan"),
            "3": _row("3", "Methods protocol for screens", "Nature", "2024 Jan"),
        },
    )

    records = fetch_candidates(client, year_min=2021, year_max=2026, max_candidates=1)

    candidates = [row for row in records if row.status == "candidate"]
    assert [row.pmid for row in candidates] == ["2"]
    assert any(row.pmid == "3" and row.status == "excluded" for row in records)


def test_corpus_store_is_append_only_and_digest_verified(tmp_path):
    store = CorpusStore(tmp_path / "corpus" / "corpus.jsonl")
    record = PaperCandidate(
        pmid="42", title="A disease target study", journal="Nature",
        year=2022, doi="10.1038/x", query_buckets=["gwas_target"],
        status="candidate",
    )

    assert store.add(record) is True
    assert store.add(record) is False
    card = store.corpus_card()
    assert card["count"] == 1
    assert card["by_status"]["candidate"] == 1
    manifest = store.write_manifest()
    assert manifest["count"] == 1
    assert manifest["records"][0]["pmid"] == "42"
    assert len(manifest["records"][0]["sha256"]) == 64

    # tampering breaks load-time digest validation
    lines = store.path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[0])
    payload["title"] = "tampered title"
    store.path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        store.all()


def test_corpus_store_add_many_is_idempotent(tmp_path):
    store = CorpusStore(tmp_path / "corpus.jsonl")
    first = PaperCandidate(
        pmid="1", title="First study", journal="Science", year=2023,
        query_buckets=["gwas_target"], status="candidate",
    )
    second = PaperCandidate(
        pmid="2", title="Second study", journal="Cell", year=2024,
        query_buckets=["multiomics_target"], status="candidate",
    )

    result = store.add_many([second, first])
    assert result == {"added": 2, "skipped": 0, "total": 2}
    repeat = store.add_many([first, second])
    assert repeat == {"added": 0, "skipped": 2, "total": 2}


def test_paper_candidate_contract_requires_status_reason_binding():
    with pytest.raises(ValueError, match="exclusion_reason"):
        PaperCandidate(
            pmid="1", title="Excluded study", journal="Nature", year=2022,
            query_buckets=["gwas_target"], status="excluded",
        )
    with pytest.raises(ValueError, match="exclusion_reason"):
        PaperCandidate(
            pmid="1", title="Candidate study", journal="Nature", year=2022,
            query_buckets=["gwas_target"], status="candidate",
            exclusion_reason="not needed",
        )
