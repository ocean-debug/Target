"""Deterministic gold-paper nomination over the candidate corpus.

Nominations are advisory. They score metadata-only candidate records
against the paper-to-strategy inclusion criteria (recent high-impact
disease-mechanism / target-discovery papers with genetics, perturbation,
single-cell or multi-omics lanes) and explicitly flag disease-coverage
gaps found by the RAG ablation (UC, psoriasis, SLE, ALS, melanoma).

A nomination never writes to the curation ledger; a paper becomes gold
only after human life-science and engineering reviewers confirm it with
`target-agent pattern curate`. Scoring is title/journal/bucket-based and
fully deterministic: no model and no network at nomination time.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import utc_now
from .paper_corpus import PaperCandidate

NOMINATION_CONTRACT_VERSION = "0.1.0"

_JOURNAL_PREMIUM = {
    "nature": 2.0, "science": 2.0, "cell": 2.0,
    "nature genetics": 1.5, "nature medicine": 1.5,
    "nature immunology": 1.2, "nature neuroscience": 1.2,
    "nature cancer": 1.2, "nature metabolism": 1.2,
    "nature cell biology": 1.0,
}

_BUCKET_BONUS = {
    "gwas_target": 1.5, "perturbation_screen": 1.5,
    "single_cell_mechanism": 1.0, "multiomics_target": 1.0,
}

# Lane signals are matched against the lowercased title only. Each lane
# contributes its bonus at most once; matched terms are recorded so a
# human reviewer can audit the reason.
_LANE_SIGNALS: dict[str, tuple[float, tuple[str, ...]]] = {
    "genetics": (2.0, (
        "gwas", "genome-wide association", "genome wide association",
        "fine-map", "fine mapping", "colocal", "eqtl", "mendelian",
        "variant", "allele", "heritability", "genetic association", "locus",
    )),
    "perturbation": (2.0, (
        "crispr", "perturb", "knockout", "knock-down", "knockdown",
        "overexpression", "loss-of-function", "gain-of-function", "screen",
    )),
    "single_cell": (1.5, (
        "single-cell", "single cell", "scrna", "spatial", "cell type",
        "atlas", "lineage", "microenvironment", "tumor microenvironment",
    )),
    "mechanism": (1.0, (
        "mechanism", "pathway", "signaling", "signalling", "axis",
        "regulat", "driver", "resistance", "immune",
    )),
    "target_drug": (1.5, (
        "target", "therapeut", "drug", "inhibitor", "agonist",
        "antagonist", "clinical", "biomarker",
    )),
}

# RAG ablation gap diseases: titles mentioning these get a bonus so the
# next curation batch is biased toward missing coverage.
_GAP_DISEASES: dict[str, tuple[str, ...]] = {
    "uc": ("ulcerative colitis", "colitis"),
    "psoriasis": ("psoriasis",),
    "sle": ("lupus", "systemic lupus"),
    "als": ("amyotrophic lateral sclerosis",),
    "melanoma": ("melanoma",),
}

# Basic-biology-only markers; strong negative signal for a disease-target
# nomination unless other disease/mechanism signals balance it.
_BASIC_BASIS_PENALTY = (
    "mouse embryo", "embryonic", "yeast", "drosophila", "zebrafish",
    "caenorhabditis",
)


class GoldNomination(BaseModel):
    """One advisory nomination record with a self-consistent digest."""

    model_config = ConfigDict(extra="forbid")

    pmid: str = Field(pattern=r"^\d+$")
    title: str = Field(min_length=1)
    journal: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    doi: str | None = None
    query_buckets: list[str] = Field(min_length=1)
    score: float
    reasons: list[str] = Field(min_length=1)
    signal_lanes: list[str] = Field(default_factory=list)
    gap_diseases: list[str] = Field(default_factory=list)
    advisory: bool = True
    status: Literal["nominated"] = "nominated"
    generated_at: str = Field(default_factory=utc_now)
    digest: str = ""

    @model_validator(mode="after")
    def _finalize(self) -> "GoldNomination":
        computed = self.compute_digest()
        if not self.digest:
            self.digest = computed
        elif self.digest != computed:
            raise ValueError(f"nomination digest mismatch for PMID {self.pmid}")
        return self

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"digest", "generated_at"})
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _normalize_journal(name: str | None) -> str:
    return re.split(r"\s*\(", str(name or "").strip().lower(), maxsplit=1)[0].strip()


def _score_record(record: PaperCandidate) -> GoldNomination | None:
    """Score one candidate record; None when it is not eligible."""
    title = (record.title or "").lower()
    score = float(_JOURNAL_PREMIUM.get(_normalize_journal(record.journal), 0.0))
    reasons: list[str] = []
    if score > 0:
        reasons.append(f"journal premium: {record.journal}")
    for bucket in record.query_buckets:
        bonus = _BUCKET_BONUS.get(bucket, 0.0)
        if bonus:
            score += bonus
            reasons.append(f"query bucket: {bucket}")
    signal_lanes: list[str] = []
    for lane, (bonus, patterns) in _LANE_SIGNALS.items():
        for pattern in patterns:
            if re.search(pattern, title):
                score += bonus
                signal_lanes.append(lane)
                reasons.append(f"title {lane} signal: {pattern}")
                break
    gap_hits: list[str] = []
    for gap_id, terms in _GAP_DISEASES.items():
        if any(re.search(term, title) for term in terms):
            score += 1.5
            gap_hits.append(gap_id)
            reasons.append(f"RAG gap disease: {gap_id}")
    for marker in _BASIC_BASIS_PENALTY:
        if re.search(marker, title):
            score -= 2.0
            reasons.append(f"basic-biology-only marker: {marker}")
    if not signal_lanes and not gap_hits:
        return None
    return GoldNomination(
        pmid=record.pmid,
        title=record.title,
        journal=record.journal,
        year=record.year,
        doi=record.doi,
        query_buckets=list(record.query_buckets),
        score=round(score, 2),
        reasons=reasons,
        signal_lanes=signal_lanes,
        gap_diseases=gap_hits,
    )


def nominate_candidates(
    records: Iterable[PaperCandidate | dict[str, Any]],
    *,
    limit: int = 40,
    min_score: float = 0.0,
    year_min: int = 2021,
) -> list[GoldNomination]:
    """Deterministically rank eligible candidate records by nomination score.

    Only corpus records with status=candidate and year >= year_min are
    considered. Scores are advisory and never imply biological quality.
    """
    nominations: list[GoldNomination] = []
    for raw in records:
        record = raw if isinstance(raw, PaperCandidate) else PaperCandidate.model_validate(raw)
        if record.status != "candidate" or record.year < year_min:
            continue
        nomination = _score_record(record)
        if nomination is None or nomination.score < min_score:
            continue
        nominations.append(nomination)
    nominations.sort(key=lambda row: (-row.score, -row.year, int(row.pmid)))
    return nominations[: max(0, limit)]


def render_nominations(nominations: Iterable[GoldNomination]) -> str:
    rows = [row.model_dump_json() for row in nominations]
    return "\n".join(rows) + ("\n" if rows else "")


def write_nominations(
    path: Path | str,
    nominations: Iterable[GoldNomination],
) -> dict[str, Any]:
    """Write nominations as append-ready JSONL plus a checksum manifest."""
    rows = list(nominations)
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    lines: list[str] = []
    for row in rows:
        line = row.model_dump_json()
        lines.append(line)
        records.append({
            "pmid": row.pmid,
            "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
        })
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    manifest = {
        "contract_version": NOMINATION_CONTRACT_VERSION,
        "nominations": len(rows),
        "generated_at": utc_now(),
        "records": records,
    }
    (target.with_name(target.stem + "_MANIFEST.json")).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    return {"path": str(target), "nominations": len(rows)}


def load_nominations(path: Path | str) -> list[GoldNomination]:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        return []
    rows: list[GoldNomination] = []
    for line_number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(GoldNomination.model_validate_json(line))
        except Exception as exc:
            raise ValueError(f"invalid nomination at line {line_number}: {exc}") from exc
    return rows
