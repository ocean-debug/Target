"""Paper-strategy curation and extraction toolchain.

Turns human-curated gold papers from the candidate corpus into validated
StrategyPattern records. The pipeline is intentionally narrow:

1. curation: an append-only ledger marks a PMID as gold or rejected (expert
   decision, machine-checkable rationale);
2. extraction: public metadata plus the abstract or the methods section are
   sent to a structured LLM backend; the result must satisfy the StrategyPattern
   contract and include at least one observed workflow;
3. storage: validated patterns are appended to the immutable PatternStore;
   an audit ledger records prompt version, model, source material level and
   errors. No full text is ever stored.

Alignment-data generation and model training are intentionally deferred and
live outside this module.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Literal, Protocol

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .contracts import utc_now
from .paper_corpus import PaperCandidate
from .paper_strategy import PatternStore, SourcePaper, StrategyPattern

CURATION_CONTRACT_VERSION = "0.1.0"
EXTRACTION_CONTRACT_VERSION = "0.1.0"
EXTRACTION_PROMPT_VERSION = "pattern-extract-v1"

_LANE_VOCABULARY = (
    "genetics, omics, single_cell, perturbation, literature, drug, safety, "
    "trials, pathology"
)


class CurationRecord(BaseModel):
    """One expert annotation decision for a corpus PMID (append-only)."""

    model_config = ConfigDict(extra="forbid")

    pmid: str = Field(pattern=r"^\d+$")
    status: Literal["gold", "rejected"]
    rationale: str = Field(min_length=1)
    annotator_role: Literal["life_science", "engineering", "lead"]
    annotated_at: str = Field(default_factory=utc_now)
    digest: str = ""

    @model_validator(mode="after")
    def _finalize(self) -> "CurationRecord":
        computed = self.compute_digest()
        if not self.digest:
            self.digest = computed
        elif self.digest != computed:
            raise ValueError(f"curation record digest mismatch for PMID {self.pmid}")
        return self

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"digest", "annotated_at"})
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class CurationStore:
    """Append-only curation ledger with latest-status semantics."""

    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()

    def _load(self) -> list[CurationRecord]:
        if not self.path.is_file():
            return []
        rows: list[CurationRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    rows.append(CurationRecord.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(f"invalid curation record at line {line_number}: {exc}") from exc
        return rows

    def add(self, record: CurationRecord) -> bool:
        if record.digest != record.compute_digest():
            raise ValueError("curation record digest is not self-consistent")
        if any(existing.digest == record.digest for existing in self._load()):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(record.model_dump_json() + "\n")
        return True

    def latest_status(self, pmid: str) -> str | None:
        status = None
        for row in self._load():
            if row.pmid == pmid:
                status = row.status
        return status

    def gold_pmids(self) -> list[str]:
        statuses: dict[str, str] = {}
        for row in self._load():
            statuses[row.pmid] = row.status
        return [pmid for pmid, status in sorted(statuses.items()) if status == "gold"]

    def card(self) -> dict[str, Any]:
        rows = self._load()
        by_status = {"gold": 0, "rejected": 0}
        for row in rows:
            by_status[row.status] += 1
        return {
            "path": str(self.path),
            "contract_version": CURATION_CONTRACT_VERSION,
            "entries": len(rows),
            "by_status": by_status,
            "gold_pmids": len(self.gold_pmids()),
        }


class PaperMeta(BaseModel):
    """Public metadata plus one bounded source text used for extraction."""

    model_config = ConfigDict(extra="forbid")

    pmid: str = Field(pattern=r"^\d+$")
    title: str = Field(min_length=1)
    journal: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    doi: str | None = None
    pmcid: str | None = None
    abstract: str | None = None
    source_text: str = Field(min_length=1)
    source_material: Literal["methods", "abstract"] = "abstract"


class MetaFetcher(Protocol):
    def fetch(self, pmid: str) -> PaperMeta | None: ...


class EuropePmcMetaFetcher:
    """Europe PMC REST metadata + bounded methods/abstract extraction.

    The methods section is preferred when the article is open access; the
    abstract is the fallback. Only the bounded text needed for extraction is
    kept in memory; it is never written to the repository.
    """

    SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    _METHOD_HEADINGS = ("method", "experimental procedure", "materials and methods")
    _MAX_METHOD_CHARS = 12000

    def __init__(self, *, timeout: float = 20.0, retries: int = 2):
        self.timeout = timeout
        self.retries = max(0, retries)

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        import time

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                if response.status_code == 429 or response.status_code >= 500:
                    raise RuntimeError(f"Europe PMC HTTP {response.status_code}")
                response.raise_for_status()
                return response
            except Exception as exc:  # pragma: no cover - network path
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1.0 + attempt)
        raise RuntimeError(f"Europe PMC request failed: {last_error}")

    def fetch(self, pmid: str) -> PaperMeta | None:
        response = self._get(self.SEARCH, {
            "query": f"EXT_ID:{pmid}",
            "format": "json",
            "resultType": "core",
        })
        payload = response.json()
        result = (payload.get("resultList") or {}).get("result") or []
        if not result:
            return None
        row = result[0]
        if str(row.get("pmid") or "") != pmid:
            return None
        abstract = (row.get("abstractText") or "").strip()
        pmcid = (row.get("pmcid") or "").strip() or None
        source_text = ""
        source_material: Literal["methods", "abstract"] = "abstract"
        if pmcid:
            try:
                methods = self._fetch_methods(pmcid)
                if methods:
                    source_text = methods
                    source_material = "methods"
            except Exception:
                source_text = ""
        if not source_text:
            source_text = abstract
        if not source_text:
            return None
        year_raw = row.get("pubYear") or row.get("firstPublicationDate") or ""
        year_digits = "".join(ch for ch in str(year_raw) if ch.isdigit())[:4]
        year = int(year_digits) if year_digits else 1900
        return PaperMeta(
            pmid=pmid,
            title=str(row.get("title") or f"untitled PMID {pmid}").strip(),
            journal=str(row.get("journalInfo", {}).get("journal", {}).get("title") or "unknown").strip(),
            year=year,
            doi=(row.get("doi") or "").strip() or None,
            pmcid=pmcid,
            abstract=abstract,
            source_text=source_text[: self._MAX_METHOD_CHARS + 2000] if source_material == "abstract" else source_text[: self._MAX_METHOD_CHARS],
            source_material=source_material,
        )

    def _fetch_methods(self, pmcid: str) -> str:
        import xml.etree.ElementTree as ET

        response = self._get(self.FULLTEXT.format(pmcid=pmcid))
        root = ET.fromstring(response.content)
        for section in root.iter():
            if section.tag.lower().endswith("sec"):
                heading = " ".join("".join(section.itertext()).split())[:240].lower()
                if any(marker in heading for marker in self._METHOD_HEADINGS):
                    text = " ".join("".join(section.itertext()).split())
                    if len(text) >= 400:
                        return text[: self._MAX_METHOD_CHARS]
        return ""


class ExtractionBackend(Protocol):
    def json_completion(self, system: str, user: str) -> dict[str, Any]: ...


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pmid: str = Field(pattern=r"^\d+$")
    pattern: StrategyPattern | None = None
    source_material: Literal["methods", "abstract"] = "abstract"
    error: str | None = None


class PatternExtractor:
    """Distill one gold paper into a StrategyPattern under deterministic gates."""

    def __init__(
        self,
        *,
        backend: ExtractionBackend,
        meta_fetcher: MetaFetcher,
        pattern_store: PatternStore,
        prompt_version: str = EXTRACTION_PROMPT_VERSION,
    ):
        self.backend = backend
        self.meta_fetcher = meta_fetcher
        self.store = pattern_store
        self.prompt_version = prompt_version

    def extract(self, paper: PaperCandidate, meta: PaperMeta | None = None) -> ExtractionResult:
        if paper.status != "candidate":
            return ExtractionResult(pmid=paper.pmid, error="only candidate corpus records can be distilled")
        if meta is None:
            try:
                meta = self.meta_fetcher.fetch(paper.pmid)
            except Exception as exc:
                return ExtractionResult(
                    pmid=paper.pmid,
                    error=f"metadata fetch failed: {exc.__class__.__name__}: {exc}",
                )
        if meta is None:
            return ExtractionResult(pmid=paper.pmid, error="no public metadata or source text available")
        system = (
            "You distill how one high-impact disease-mechanism or target-discovery paper "
            "chose its evidence path. Return exactly one JSON object conforming to the "
            "StrategyPattern contract. Never invent evidence layers, datasets or results "
            "that are absent from the supplied source text. Never emit shell commands or "
            "analysis code."
        )
        user = json.dumps({
            "prompt_version": self.prompt_version,
            "paper": {
                "pmid": paper.pmid,
                "title": meta.title,
                "journal": meta.journal,
                "year": meta.year,
                "doi": meta.doi,
                "pmcid": meta.pmcid,
            },
            "source_material": meta.source_material,
            "source_text": meta.source_text,
            "lane_vocabulary": _LANE_VOCABULARY,
            "contract_rules": [
                "pattern_id is assigned by the system, do not return it",
                "evidence_start_lane must be one of ordered_lanes",
                "required_lanes and optional_lanes must be subsets of ordered_lanes",
                "ordered_lanes must not repeat lanes",
                "evidence_links requires at least one link with decision_rule and why_this_link",
                "stop_downgrade_rules requires at least one concrete rule",
                "observed_workflows requires at least one entry with steps that reflect the paper",
                "mark uncertainty in boundary_notes instead of inventing facts",
            ],
            "required_output": {
                "name": "short pattern name",
                "disease_class": "disease or disease family",
                "disease_keywords": ["searchable keywords"],
                "applicability": ["conditions under which this order is worth trying"],
                "evidence_start_lane": "chosen primary lane",
                "ordered_lanes": ["ordered evidence lanes"],
                "required_lanes": ["lanes the pattern cannot proceed without"],
                "optional_lanes": ["optional validation lanes"],
                "evidence_links": [{"link_id": "...", "source_lane": "...", "target_lane": "...",
                                    "link_type": "...", "evidence_used": ["..."], "decision_rule": "...",
                                    "why_this_link": "..."}],
                "stop_downgrade_rules": ["when to stop or downgrade a claim"],
                "mixed_method_rationale": "why this evidence order was chosen",
                "boundary_notes": ["what this pattern cannot conclude"],
                "observed_workflows": [{"workflow_id": "wf-" + paper.pmid, "paper_title": meta.title,
                                        "journal": meta.journal, "year": meta.year, "disease": "...",
                                        "data_availability": [{"lane": "...", "available": True,
                                                               "source": "...", "notes": "..."}],
                                        "steps": [{"operation": "...", "tool_abstraction": "...",
                                                   "input_lanes": ["..."], "output_lanes": ["..."],
                                                   "decision_gate": "...", "why_this_step": "..."}],
                                        "rationale": "..."}],
            },
        }, ensure_ascii=False)
        try:
            raw = self.backend.json_completion(system, user)
        except Exception as exc:
            return ExtractionResult(pmid=paper.pmid, error=f"LLM backend failed: {exc.__class__.__name__}: {exc}")
        if not isinstance(raw, dict):
            return ExtractionResult(pmid=paper.pmid, error="LLM output is not a JSON object")
        raw.pop("pattern_id", None)
        raw.pop("review", None)
        raw.pop("digest", None)
        raw.pop("created_at", None)
        raw.pop("source_papers", None)
        raw["pattern_id"] = f"pattern-{paper.pmid}"
        raw["source_papers"] = [SourcePaper(
            title=meta.title,
            journal=meta.journal,
            year=meta.year,
            doi=meta.doi,
            pmcid=meta.pmcid,
        ).model_dump(mode="json")]
        try:
            pattern = StrategyPattern.model_validate(raw)
        except ValidationError as exc:
            messages = "; ".join(
                f"{'.'.join(str(p) for p in error.get('loc', []))}: {error.get('msg', '')}"
                for error in exc.errors(include_url=False, include_input=False)
            )
            return ExtractionResult(
                pmid=paper.pmid,
                source_material=meta.source_material,
                error=f"extracted pattern failed schema validation: {messages}",
            )
        except ValueError as exc:
            return ExtractionResult(
                pmid=paper.pmid,
                source_material=meta.source_material,
                error=f"extracted pattern failed integrity checks: {exc}",
            )
        if not pattern.observed_workflows:
            return ExtractionResult(
                pmid=paper.pmid,
                source_material=meta.source_material,
                error="extracted pattern has no observed_workflows entry",
            )
        try:
            added = self.store.add(pattern)
        except Exception as exc:
            return ExtractionResult(
                pmid=paper.pmid,
                source_material=meta.source_material,
                error=f"pattern store rejected record: {exc}",
            )
        if not added:
            return ExtractionResult(
                pmid=paper.pmid,
                source_material=meta.source_material,
                error=f"pattern {pattern.pattern_id} already exists in the store",
            )
        return ExtractionResult(pmid=paper.pmid, pattern=pattern, source_material=meta.source_material)

    def extract_many(self, papers: Iterable[PaperCandidate]) -> list[ExtractionResult]:
        return [self.extract(paper) for paper in papers]


class ExtractionAuditRecord(BaseModel):
    """One machine-checkable audit row per extraction attempt."""

    model_config = ConfigDict(extra="forbid")

    pmid: str = Field(pattern=r"^\d+$")
    pattern_id: str | None = None
    status: Literal["added", "failed"]
    source_material: Literal["methods", "abstract"] = "abstract"
    error: str | None = None
    prompt_version: str = EXTRACTION_PROMPT_VERSION
    created_at: str = Field(default_factory=utc_now)
    digest: str = ""

    @model_validator(mode="after")
    def _finalize(self) -> "ExtractionAuditRecord":
        if self.status == "added" and self.pattern_id is None:
            raise ValueError("added extraction audit requires pattern_id")
        if self.status == "failed" and not self.error:
            raise ValueError("failed extraction audit requires error")
        computed = self.compute_digest()
        if not self.digest:
            self.digest = computed
        elif self.digest != computed:
            raise ValueError(f"extraction audit digest mismatch for PMID {self.pmid}")
        return self

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"digest", "created_at"})
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ExtractionAuditStore:
    """Append-only audit ledger for extraction attempts."""

    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()

    def _load(self) -> list[ExtractionAuditRecord]:
        if not self.path.is_file():
            return []
        rows: list[ExtractionAuditRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    rows.append(ExtractionAuditRecord.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(f"invalid extraction audit at line {line_number}: {exc}") from exc
        return rows

    def add(self, record: ExtractionAuditRecord) -> bool:
        if record.digest != record.compute_digest():
            raise ValueError("extraction audit digest is not self-consistent")
        if any(existing.digest == record.digest for existing in self._load()):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(record.model_dump_json() + "\n")
        return True

    def card(self) -> dict[str, Any]:
        rows = self._load()
        return {
            "path": str(self.path),
            "contract_version": EXTRACTION_CONTRACT_VERSION,
            "entries": len(rows),
            "added": sum(1 for row in rows if row.status == "added"),
            "failed": sum(1 for row in rows if row.status == "failed"),
        }


def run_extraction(
    *,
    papers: list[PaperCandidate],
    pattern_store: PatternStore,
    extractor: PatternExtractor,
    audit_store: ExtractionAuditStore,
    pmids: list[str] | None = None,
) -> dict[str, Any]:
    """Run extraction over the supplied corpus records (already curated)."""
    selected = list(papers)
    if pmids:
        wanted = set(pmids)
        selected = [row for row in selected if row.pmid in wanted]
    results: list[ExtractionResult] = []
    for paper in selected:
        result = extractor.extract(paper)
        results.append(result)
        audit = ExtractionAuditRecord(
            pmid=paper.pmid,
            pattern_id=result.pattern.pattern_id if result.pattern else None,
            status="added" if result.pattern else "failed",
            source_material=result.source_material,
            error=result.error,
            prompt_version=extractor.prompt_version,
        )
        audit_store.add(audit)
    return {
        "requested": [paper.pmid for paper in selected],
        "results": [
            {
                "pmid": result.pmid,
                "pattern_id": result.pattern.pattern_id if result.pattern else None,
                "source_material": result.source_material,
                "error": result.error,
            }
            for result in results
        ],
        "added": sum(1 for result in results if result.pattern is not None),
        "failed": sum(1 for result in results if result.pattern is None),
    }


__all__ = [
    "CURATION_CONTRACT_VERSION", "EXTRACTION_CONTRACT_VERSION",
    "EXTRACTION_PROMPT_VERSION", "CurationRecord", "CurationStore",
    "ExtractionAuditRecord", "ExtractionAuditStore", "ExtractionBackend",
    "ExtractionResult", "EuropePmcMetaFetcher", "MetaFetcher", "PaperMeta",
    "PatternExtractor", "run_extraction",
]
