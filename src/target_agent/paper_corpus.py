"""PubMed/E-utilities candidate corpus for paper-derived strategy patterns.

Builds a deterministic, append-only candidate pool of recent high-impact
disease-mechanism / target-discovery papers (Nature, Science, Cell and select
Nature research journals). The corpus is metadata-only: PMID, title, journal,
year, DOI, PMCID and the query buckets that found the paper. No full text and
no abstracts are stored; pattern distillation happens later under expert
review (P1.2).

NCBI E-utilities are the only network dependency. The transport is injected
so tests can exercise filtering and store semantics without network access.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import utc_now

CORPUS_CONTRACT_VERSION = "0.1.0"

# Journal whitelist: CNS plus high-impact Nature research journals that
# regularly publish disease-mechanism / target-discovery studies.
JOURNAL_WHITELIST = frozenset({
    "nature", "science", "cell", "nature genetics", "nature medicine",
    "nature immunology", "nature neuroscience", "nature cancer",
    "nature metabolism", "nature cell biology",
})

# Deterministic query buckets; each term is combined with one journal filter.
QUERY_BUCKETS: tuple[tuple[str, str], ...] = (
    ("gwas_target",
     '("genome-wide association" OR GWAS OR "fine-mapping" OR colocalization '
     'OR eQTL) AND (target OR mechanism OR causal OR drug)'),
    ("single_cell_mechanism",
     '("single-cell" OR scRNA-seq OR "spatial transcriptomics") AND '
     '(disease OR tumor) AND (mechanism OR target OR microenvironment)'),
    ("perturbation_screen",
     '("CRISPR screen" OR "Perturb-seq" OR "genetic perturbation" OR '
     '"drug screen") AND (disease OR mechanism OR target)'),
    ("multiomics_target",
     '("multi-omics" OR multiomics OR proteomics OR metabolomics) AND '
     '(disease) AND (target OR mechanism OR drug)'),
)

# Titles matching these markers are treated as methods-only or review content
# and kept in the corpus as excluded records with a machine-checkable reason.
_TITLE_EXCLUSION = re.compile(
    r"\b(review|protocol|software|toolkit|benchmark|algorithm|pipeline|"
    r"workflow|database|resource|white paper)\b",
    re.IGNORECASE,
)
_YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


def parse_year(pubdate: str | None) -> int | None:
    if not pubdate:
        return None
    match = _YEAR_PATTERN.search(pubdate)
    return int(match.group(0)) if match else None


class EutilsClient(Protocol):
    """Minimal E-utilities surface used by the corpus builder."""

    def search(
        self,
        bucket_id: str,
        terms: str,
        journal: str,
        year_min: int,
        year_max: int,
        retmax: int,
    ) -> list[str]: ...

    def summary(self, pmids: list[str]) -> dict[str, dict[str, Any]]: ...


class RequestsEutilsClient:
    """Production E-utilities client backed by requests with bounded retries."""

    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(
        self,
        *,
        email: str | None = None,
        api_key: str | None = None,
        timeout: float = 20.0,
        retries: int = 2,
    ):
        import requests

        self._requests = requests
        self.email = email
        self.api_key = api_key
        self.timeout = timeout
        self.retries = max(0, retries)
        self._sleep = 0.35  # polite E-utilities rate limiting between calls

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        import time

        url = f"{self.BASE}/{endpoint}.fcgi"
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self._requests.get(url, params=params, timeout=self.timeout)
                if response.status_code == 429 or response.status_code >= 500:
                    raise RuntimeError(f"E-utilities HTTP {response.status_code}")
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # pragma: no cover - network path
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1.0 + attempt)
        raise RuntimeError(f"E-utilities request failed: {last_error}")

    def search(
        self,
        bucket_id: str,
        terms: str,
        journal: str,
        year_min: int,
        year_max: int,
        retmax: int,
    ) -> list[str]:
        import time

        params: dict[str, Any] = {
            "db": "pubmed",
            "term": f'{terms} AND "{journal}"[Journal]',
            "retmode": "json",
            "retmax": str(retmax),
            "datetype": "pdat",
            "mindate": f"{year_min}/01/01",
            "maxdate": f"{year_max}/12/31",
        }
        if self.email:
            params["tool"] = "target-discovery-paper-corpus"
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        payload = self._get("esearch", params)
        time.sleep(self._sleep)
        return [str(item) for item in (payload.get("esearchresult", {}).get("idlist") or [])]

    def summary(self, pmids: list[str]) -> dict[str, dict[str, Any]]:
        if not pmids:
            return {}
        params: dict[str, Any] = {
            "db": "pubmed",
            "retmode": "json",
            "id": ",".join(pmids),
        }
        if self.email:
            params["tool"] = "target-discovery-paper-corpus"
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        payload = self._get("esummary", params)
        result = payload.get("result") or {}
        rows: dict[str, dict[str, Any]] = {}
        for uid in result.get("uids") or []:
            row = result.get(str(uid)) or {}
            if isinstance(row, dict):
                rows[str(uid)] = row
        return rows


class PaperCandidate(BaseModel):
    """One immutable metadata record in the candidate corpus."""

    model_config = ConfigDict(extra="forbid")

    pmid: str = Field(pattern=r"^\d+$")
    title: str = Field(min_length=1)
    journal: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    doi: str | None = None
    pmcid: str | None = None
    query_buckets: list[str] = Field(min_length=1)
    status: Literal["candidate", "excluded"]
    exclusion_reason: str | None = None
    fetched_at: str = Field(default_factory=utc_now)
    digest: str = ""

    @model_validator(mode="after")
    def _finalize(self) -> "PaperCandidate":
        if self.status == "excluded" and not self.exclusion_reason:
            raise ValueError("excluded corpus record requires exclusion_reason")
        if self.status == "candidate" and self.exclusion_reason:
            raise ValueError("candidate corpus record cannot carry exclusion_reason")
        computed = self.compute_digest()
        if not self.digest:
            self.digest = computed
        elif self.digest != computed:
            raise ValueError(f"corpus record digest mismatch for PMID {self.pmid}")
        return self

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"digest", "fetched_at"})
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _normalize_journal(name: str | None) -> str:
    """Normalize NCBI full journal names, e.g. 'Science (New York, N.Y.)' -> 'science'."""
    return re.split(r"\s*\(", str(name or "").strip().lower(), maxsplit=1)[0].strip()


def _classify(
    row: dict[str, Any],
    *,
    year_min: int,
    year_max: int,
) -> tuple[Literal["candidate", "excluded"], str | None]:
    journal = _normalize_journal(row.get("fulljournalname"))
    if journal not in JOURNAL_WHITELIST:
        return "excluded", f"journal not in whitelist: {journal or 'unknown'}"
    year = parse_year(str(row.get("pubdate") or ""))
    if year is None or not year_min <= year <= year_max:
        return "excluded", f"publication year outside {year_min}-{year_max}: {row.get('pubdate') or 'unknown'}"
    title = str(row.get("title") or "").strip()
    if not title:
        return "excluded", "missing title"
    match = _TITLE_EXCLUSION.search(title)
    if match:
        return "excluded", f"title indicates review/methods-only content: {match.group(0)}"
    return "candidate", None


def _article_id(row: dict[str, Any], idtype: str) -> str | None:
    for item in row.get("articleids") or []:
        if isinstance(item, dict) and str(item.get("idtype") or "") == idtype:
            value = str(item.get("value") or "").strip()
            if value:
                return value
    return None


def _chunks(items: list[str], size: int = 100) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def fetch_candidates(
    client: EutilsClient,
    *,
    year_min: int = 2021,
    year_max: int = 2026,
    retmax_per_query: int = 8,
    max_candidates: int = 200,
) -> list[PaperCandidate]:
    """Fetch, deduplicate and deterministically classify candidate records.

    The returned list is sorted by (year desc, pmid) and candidate records are
    capped at max_candidates; excluded records are always retained for audit.
    """
    found: dict[str, set[str]] = {}
    for bucket_id, terms in QUERY_BUCKETS:
        for journal in sorted(JOURNAL_WHITELIST):
            for pmid in client.search(bucket_id, terms, journal, year_min, year_max, retmax_per_query):
                found.setdefault(str(pmid), set()).add(bucket_id)
    summaries: dict[str, dict[str, Any]] = {}
    for batch in _chunks(sorted(found)):
        summaries.update(client.summary(batch))
    records: list[PaperCandidate] = []
    for pmid in sorted(found):
        row = summaries.get(pmid) or {}
        status, reason = _classify(row, year_min=year_min, year_max=year_max)
        records.append(PaperCandidate(
            pmid=pmid,
            title=str(row.get("title") or f"untitled PMID {pmid}").strip(),
            journal=str(row.get("fulljournalname") or "unknown").strip(),
            year=parse_year(str(row.get("pubdate") or "")) or 1900,
            doi=_article_id(row, "doi"),
            pmcid=_article_id(row, "pmc"),
            query_buckets=sorted(found[pmid]),
            status=status,
            exclusion_reason=reason,
        ))
    records.sort(key=lambda row: (-row.year, row.pmid))
    candidates = [row for row in records if row.status == "candidate"][:max(0, max_candidates)]
    excluded = [row for row in records if row.status == "excluded"]
    return [*candidates, *excluded]


class CorpusStore:
    """Append-only JSONL corpus store with per-record digest validation."""

    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()

    def _load(self) -> list[PaperCandidate]:
        if not self.path.is_file():
            return []
        rows: list[PaperCandidate] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    rows.append(PaperCandidate.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(f"invalid corpus record at line {line_number}: {exc}") from exc
        return rows

    def all(self) -> list[PaperCandidate]:
        return self._load()

    def add(self, record: PaperCandidate) -> bool:
        existing = {row.pmid for row in self._load()}
        if record.pmid in existing:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(record.model_dump_json() + "\n")
        return True

    def add_many(self, records: Iterable[PaperCandidate]) -> dict[str, int]:
        known = {row.pmid for row in self._load()}
        added = 0
        skipped = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            for record in sorted(records, key=lambda row: row.pmid):
                if record.pmid in known:
                    skipped += 1
                    continue
                handle.write(record.model_dump_json() + "\n")
                known.add(record.pmid)
                added += 1
        return {"added": added, "skipped": skipped, "total": len(self._load())}

    def corpus_card(self) -> dict[str, Any]:
        rows = self._load()
        by_status = {"candidate": 0, "excluded": 0}
        journals: dict[str, int] = {}
        years: dict[str, int] = {}
        for row in rows:
            by_status[row.status] = by_status.get(row.status, 0) + 1
            journals[row.journal] = journals.get(row.journal, 0) + 1
            years[str(row.year)] = years.get(str(row.year), 0) + 1
        return {
            "path": str(self.path),
            "contract_version": CORPUS_CONTRACT_VERSION,
            "count": len(rows),
            "by_status": by_status,
            "journals": dict(sorted(journals.items(), key=lambda pair: (-pair[1], pair[0]))),
            "years": dict(sorted(years.items())),
        }

    def write_manifest(self) -> dict[str, Any]:
        rows = self._load()
        manifest = {
            "contract_version": CORPUS_CONTRACT_VERSION,
            "count": len(rows),
            "by_status": {
                status: sum(1 for row in rows if row.status == status)
                for status in ("candidate", "excluded")
            },
            "records": [
                {
                    "pmid": row.pmid,
                    "sha256": hashlib.sha256(
                        row.model_dump_json().encode("utf-8")
                    ).hexdigest(),
                }
                for row in rows
            ],
        }
        manifest_path = self.path.with_name("MANIFEST.json")
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
        return manifest


def corpus_store_from_path(path: Path | str | None) -> CorpusStore | None:
    if not path:
        return None
    store = CorpusStore(path)
    if not store.path.is_file():
        return None
    return store


__all__ = [
    "CORPUS_CONTRACT_VERSION", "CorpusStore", "EutilsClient",
    "JOURNAL_WHITELIST", "PaperCandidate", "QUERY_BUCKETS",
    "RequestsEutilsClient", "corpus_store_from_path", "fetch_candidates",
    "parse_year", "_normalize_journal",
]
