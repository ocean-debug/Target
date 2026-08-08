"""Paper-derived evidence strategy patterns: contracts, store, retrieval, few-shot.

Implements the Paper-to-Strategy P0/P1 slice of the product plan:

- immutable pattern records (ObservedWorkflow / StrategyPattern /
  BestPracticePattern / EvidenceLink);
- a deterministic lexical PatternStore whose retrieval respects the data
  actually available for the task;
- a few-shot block used by the project Planner.

Alignment-data generation and model training are intentionally deferred (P3)
and are not part of this module.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .contracts import utc_now

PATTERN_CONTRACT_VERSION = "0.1.0"
_LANE_TOKEN = re.compile(r"[a-z0-9]+")
_CJK_TOKEN = re.compile(r"[\u4e00-\u9fff]+")


def _tokens(text: str) -> set[str]:
    lowered = (text or "").lower()
    tokens = set(_LANE_TOKEN.findall(lowered))
    tokens.update(_CJK_TOKEN.findall(lowered))
    tokens.discard("")
    return tokens


class ReviewGate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    life_science_review: Literal["pending", "approved", "rejected"] = "pending"
    engineering_review: Literal["pending", "approved", "rejected"] = "pending"


class ReviewEntry(BaseModel):
    """One expert review decision for a pattern (append-only ledger)."""

    model_config = ConfigDict(extra="forbid")

    pattern_id: str = Field(pattern=r"^pattern-[a-z0-9][a-z0-9-]*$")
    role: Literal["life_science", "engineering"]
    status: Literal["approved", "rejected"]
    reviewed_at: str = Field(default_factory=utc_now)
    digest: str = ""

    @model_validator(mode="after")
    def _finalize(self) -> "ReviewEntry":
        computed = self.compute_digest()
        if not self.digest:
            self.digest = computed
        elif self.digest != computed:
            raise ValueError(f"review entry digest mismatch for {self.pattern_id}")
        return self

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"digest", "reviewed_at"})
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ReviewLedger:
    """Append-only expert review ledger.

    Pattern records stay immutable; review approvals are layered on top so
    later status changes never rewrite history.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()

    def _load(self) -> list[ReviewEntry]:
        if not self.path.is_file():
            return []
        rows: list[ReviewEntry] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    rows.append(ReviewEntry.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(f"invalid review entry at line {line_number}: {exc}") from exc
        return rows

    def add(self, entry: ReviewEntry) -> bool:
        if entry.digest != entry.compute_digest():
            raise ValueError("review entry digest is not self-consistent")
        if any(existing.digest == entry.digest for existing in self._load()):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(entry.model_dump_json() + "\n")
        return True

    def status(self, pattern_id: str) -> dict[str, Literal["approved", "rejected"]]:
        latest: dict[str, Literal["approved", "rejected"]] = {}
        for row in self._load():
            if row.pattern_id == pattern_id:
                latest[row.role] = row.status
        return latest

    def effective_gate(self, pattern: StrategyPattern) -> ReviewGate:
        merged = pattern.review.model_copy()
        latest = self.status(pattern.pattern_id)
        if "life_science" in latest:
            merged.life_science_review = latest["life_science"]
        if "engineering" in latest:
            merged.engineering_review = latest["engineering"]
        return merged

    def pending_count(self, patterns: Iterable[StrategyPattern]) -> int:
        return sum(
            1 for pattern in patterns
            if self.effective_gate(pattern).life_science_review != "approved"
            or self.effective_gate(pattern).engineering_review != "approved"
        )

    def card(self) -> dict[str, Any]:
        rows = self._load()
        by_role = {"life_science": {"approved": 0, "rejected": 0}, "engineering": {"approved": 0, "rejected": 0}}
        for row in rows:
            by_role[row.role][row.status] += 1
        return {"path": str(self.path), "entries": len(rows), "by_role": by_role}


class DataAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lane: str = Field(min_length=1)
    available: bool
    source: str | None = None
    notes: str | None = None


class ObservedStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str = Field(min_length=1)
    tool_abstraction: str | None = None
    input_lanes: list[str] = Field(default_factory=list)
    output_lanes: list[str] = Field(default_factory=list)
    decision_gate: str | None = None
    why_this_step: str | None = None


class ObservedWorkflow(BaseModel):
    """What one paper actually did; kept separate from strategy abstraction."""

    model_config = ConfigDict(extra="forbid")
    workflow_id: str = Field(min_length=1)
    paper_title: str = Field(min_length=1)
    journal: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    doi: str | None = None
    pmcid: str | None = None
    disease: str = Field(min_length=1)
    disease_context: dict[str, str] = Field(default_factory=dict)
    data_availability: list[DataAvailability] = Field(default_factory=list)
    steps: list[ObservedStep] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class EvidenceLink(BaseModel):
    """How one evidence layer is connected to another in the paper."""

    model_config = ConfigDict(extra="forbid")
    link_id: str = Field(min_length=1)
    source_lane: str = Field(min_length=1)
    target_lane: str = Field(min_length=1)
    link_type: str = Field(min_length=1)
    evidence_used: list[str] = Field(default_factory=list)
    decision_rule: str = Field(min_length=1)
    why_this_link: str = Field(min_length=1)
    independence_note: str | None = None


class SourcePaper(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    journal: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    doi: str | None = None
    pmcid: str | None = None


class StrategyPattern(BaseModel):
    """Conditional evidence-strategy pattern distilled from high-quality research.

    A pattern is a hypothesis about which evidence order is worth trying under
    which conditions; it is never evidence for a current task and never a
    replacement for the deterministic scientific gates.
    """

    model_config = ConfigDict(extra="forbid")

    pattern_id: str = Field(pattern=r"^pattern-[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1)
    version: str = "1.0.0"
    validation_level: Literal["discovery_pattern", "best_practice"] = "discovery_pattern"
    disease_class: str = Field(min_length=1)
    disease_keywords: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(min_length=1)
    evidence_start_lane: str = Field(min_length=1)
    ordered_lanes: list[str] = Field(min_length=1)
    required_lanes: list[str] = Field(min_length=1)
    optional_lanes: list[str] = Field(default_factory=list)
    evidence_links: list[EvidenceLink] = Field(min_length=1)
    stop_downgrade_rules: list[str] = Field(min_length=1)
    mixed_method_rationale: str = Field(min_length=1)
    boundary_notes: list[str] = Field(default_factory=list)
    observed_workflows: list[ObservedWorkflow] = Field(default_factory=list)
    source_papers: list[SourcePaper] = Field(min_length=1)
    review: ReviewGate = Field(default_factory=ReviewGate)
    created_at: str = Field(default_factory=utc_now)
    digest: str = ""

    @model_validator(mode="after")
    def _finalize(self) -> "StrategyPattern":
        ordered = list(dict.fromkeys(self.ordered_lanes))
        if ordered != self.ordered_lanes:
            raise ValueError("ordered_lanes must not repeat a lane")
        if self.evidence_start_lane not in ordered:
            raise ValueError("evidence_start_lane must appear in ordered_lanes")
        missing_required = set(self.required_lanes) - set(ordered)
        if missing_required:
            raise ValueError(f"required lanes missing from ordered_lanes: {sorted(missing_required)}")
        unknown_optional = set(self.optional_lanes) - set(ordered)
        if unknown_optional:
            raise ValueError(f"optional lanes missing from ordered_lanes: {sorted(unknown_optional)}")
        computed = self.compute_digest()
        if not self.digest:
            self.digest = computed
        elif self.digest != computed:
            raise ValueError(f"pattern digest mismatch for {self.pattern_id}")
        return self

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"digest", "review", "created_at"})
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class BestPracticePattern(StrategyPattern):
    """A strategy pattern that has additionally passed expert and benchmark validation."""

    model_config = ConfigDict(extra="forbid")
    validation_level: Literal["discovery_pattern", "best_practice"] = "best_practice"
    validated_by: list[str] = Field(min_length=1)
    validation_refs: list[str] = Field(min_length=1)


def _parse_pattern_line(line: str) -> StrategyPattern:
    try:
        return StrategyPattern.model_validate_json(line)
    except ValidationError as strategy_error:
        try:
            return BestPracticePattern.model_validate_json(line)
        except ValidationError:
            raise strategy_error


class PatternHit(BaseModel):
    pattern: StrategyPattern
    score: float
    matched_reason: list[str] = Field(default_factory=list)


def _score_pattern(
    pattern: StrategyPattern,
    query_tokens: set[str],
    disease_tokens: set[str],
    lanes_available: set[str] | None,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if disease_tokens:
        disease_hay = _tokens(" ".join([pattern.disease_class, *pattern.disease_keywords]))
        hits = disease_tokens & disease_hay
        if hits:
            score += 3.0 * len(hits)
            reasons.append(f"disease keywords matched: {sorted(hits)}")
    if query_tokens:
        hay = _tokens(" ".join([
            pattern.name, pattern.disease_class, *pattern.applicability,
            pattern.mixed_method_rationale, *pattern.boundary_notes,
            *[link.link_type for link in pattern.evidence_links],
        ]))
        hits = query_tokens & hay
        if hits:
            score += 1.0 * len(hits)
            reasons.append("query terms matched pattern text")
    if lanes_available is not None:
        missing = set(pattern.required_lanes) - lanes_available
        if not missing:
            score += 4.0
            reasons.append("all required lanes are available")
        else:
            score -= 6.0 * len(missing)
            reasons.append(f"missing required lanes: {sorted(missing)}")
        if pattern.evidence_start_lane in lanes_available:
            score += 2.0
            reasons.append(f"start lane {pattern.evidence_start_lane} is available")
        else:
            score -= 2.0
            reasons.append(f"start lane {pattern.evidence_start_lane} unavailable")
    if pattern.validation_level == "best_practice":
        score += 1.0
        reasons.append("validated best-practice pattern")
    if max((paper.year for paper in pattern.source_papers), default=0) >= 2021:
        score += 1.0
        reasons.append("recent source paper (>=2021)")
    return score, reasons


class PatternStore:
    """Append-only JSONL pattern store with deterministic lexical retrieval.

    Retrieval is intentionally deterministic: no embedding model, no network.
    The store only needs stable pattern records; ranking is a strategy hint,
    not a claim about the current task.
    """

    def __init__(self, path: Path | str, review_ledger_path: Path | str | None = None):
        self.path = Path(path).expanduser().resolve()
        self.review_ledger = ReviewLedger(review_ledger_path) if review_ledger_path else None

    def _load(self) -> list[StrategyPattern]:
        if not self.path.is_file():
            return []
        rows: list[StrategyPattern] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    rows.append(_parse_pattern_line(line))
                except Exception as exc:
                    raise ValueError(f"invalid pattern record at line {line_number}: {exc}") from exc
        return rows

    def add(self, pattern: StrategyPattern | BestPracticePattern | dict[str, Any]) -> bool:
        if isinstance(pattern, dict):
            try:
                record: StrategyPattern = StrategyPattern.model_validate(pattern)
            except ValidationError:
                record = BestPracticePattern.model_validate(pattern)
        elif isinstance(pattern, (StrategyPattern, BestPracticePattern)):
            record = pattern
        else:
            raise TypeError("pattern must be a StrategyPattern or dict")
        if record.digest != record.compute_digest():
            raise ValueError("pattern digest is not self-consistent")
        existing = {row.pattern_id for row in self._load()}
        if record.pattern_id in existing:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(record.model_dump_json() + "\n")
        return True

    def get(self, pattern_id: str) -> StrategyPattern | None:
        return next((row for row in self._load() if row.pattern_id == pattern_id), None)

    def all(self) -> list[StrategyPattern]:
        return self._load()

    def search(
        self,
        *,
        query: str = "",
        disease: str | None = None,
        lanes_available: Iterable[str] | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[PatternHit]:
        query_tokens = _tokens(query)
        disease_tokens = _tokens(disease or "")
        available = {str(lane).lower() for lane in lanes_available} if lanes_available is not None else None
        scored: list[PatternHit] = []
        for pattern in self._load():
            score, reasons = _score_pattern(pattern, query_tokens, disease_tokens, available)
            if score >= min_score:
                scored.append(PatternHit(pattern=pattern, score=score, matched_reason=reasons))
        scored.sort(key=lambda hit: (-hit.score, hit.pattern.pattern_id))
        return scored[: max(0, top_k)]

    def _pending_review_count(self, rows: list[StrategyPattern]) -> int:
        if self.review_ledger is not None:
            return self.review_ledger.pending_count(rows)
        return sum(
            1 for row in rows
            if row.review.life_science_review != "approved" or row.review.engineering_review != "approved"
        )

    def corpus_card(self) -> dict[str, Any]:
        rows = self._load()
        return {
            "path": str(self.path),
            "contract_version": PATTERN_CONTRACT_VERSION,
            "count": len(rows),
            "validation_levels": {
                level: sum(1 for row in rows if row.validation_level == level)
                for level in ("discovery_pattern", "best_practice")
            },
            "review_pending": self._pending_review_count(rows),
            "review_ledger_configured": self.review_ledger is not None,
        }


class PlannerFewShotBuilder:
    """Build a compact, auditable few-shot block for the project Planner."""

    def __init__(self, store: PatternStore | None = None, top_k: int = 3):
        self.store = store
        self.top_k = max(0, min(top_k, 8))

    def build(
        self,
        *,
        disease: str,
        tissue: str | None = None,
        cell_type: str | None = None,
        data_availability: dict[str, bool] | None = None,
    ) -> list[dict[str, Any]]:
        if self.store is None or self.top_k == 0 or not disease:
            return []
        available = {lane for lane, flag in (data_availability or {}).items() if flag}
        query = " ".join(part for part in (disease, tissue or "", cell_type or "") if part)
        hits = self.store.search(
            query=query,
            disease=disease,
            lanes_available=available or None,
            top_k=self.top_k,
            min_score=0.5,
        )
        return [self._render(hit) for hit in hits]

    @staticmethod
    def _render(hit: PatternHit) -> dict[str, Any]:
        pattern = hit.pattern
        return {
            "pattern_id": pattern.pattern_id,
            "name": pattern.name,
            "validation_level": pattern.validation_level,
            "problem_shape": {
                "disease_class": pattern.disease_class,
                "applicability": pattern.applicability[:4],
            },
            "chosen_start": pattern.evidence_start_lane,
            "ordered_lanes": pattern.ordered_lanes,
            "why_this_order": pattern.mixed_method_rationale,
            "stop_rules": pattern.stop_downgrade_rules[:4],
            "strategy_hint_not_evidence": True,
            "score": round(hit.score, 2),
            "matched_reason": hit.matched_reason[:4],
        }


def infer_data_availability(context: dict[str, Any]) -> dict[str, bool] | None:
    """Infer which evidence lanes the task context can actually supply.

    Returns None when the context gives no signal, so retrieval does not
    penalize patterns based on guessed availability.
    """
    if not isinstance(context, dict):
        return None
    keys = {str(key).lower(): value for key, value in context.items()}

    def has(*names: str) -> bool:
        return any(bool(keys.get(name)) for name in names)

    genetics = has("gwas_summary_stats", "gwas_available", "genetics_available", "lead_snp", "fine_mapping")
    omics = has("preferred_dataset_accessions", "geo_accession", "omics_available", "datasets", "h5ad_path")
    perturbation = has("perturbation_available", "perturbation_oracle", "perturbation_data")
    drug = has("drug_available", "known_drugs", "drug_match_available")
    if not any((genetics, omics, perturbation, drug)):
        return None
    return {
        "genetics": genetics,
        "omics": omics,
        "perturbation": perturbation,
        "literature": True,
        "drug": drug,
        "safety": True,
    }


def pattern_store_from_path(path: Path | str | None) -> PatternStore | None:
    if not path:
        return None
    store = PatternStore(path)
    if not store.path.is_file():
        return None
    return store


__all__ = [
    "PATTERN_CONTRACT_VERSION", "BestPracticePattern", "DataAvailability",
    "EvidenceLink", "ObservedStep", "ObservedWorkflow", "PatternHit",
    "PatternStore", "PlannerFewShotBuilder", "ReviewEntry", "ReviewGate",
    "ReviewLedger", "SourcePaper", "StrategyPattern", "infer_data_availability",
    "pattern_store_from_path",
]
