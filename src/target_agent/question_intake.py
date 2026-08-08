"""Natural-language research question intake -> reviewable draft project spec.

A free-form question becomes a *draft* ResearchProjectSpec without
reserving or executing anything. Extraction is deliberately conservative:

- The LLM (Step) may propose structured fields, but deterministic gates
  decide precedence: explicit hints > curated disease-library match >
  LLM proposal > missing. Fields that cannot be established stay missing;
  the draft never invents tissue, cell type, stage or phenotype.
- A curated disease match supplies the canonical name and ontology id;
  its benchmark default context is only reported as a suggestion in
  review_notes, never injected into the project.
- The draft is flagged needs_review whenever a field is missing, comes
  from low-confidence extraction, the disease is not in the curated
  library, or the LLM was unavailable.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .diseases import DiseaseEntry, load_library
from .llm import LLMUnavailable, StepClient
from .research_contracts import AutonomyMode, ResearchProjectSpec
from .research_service import ResearchProjectService
from .research_runtime import ResearchProjectRuntime

QUESTION_INTAKE_VERSION = "0.1.0"

BRIEF_FIELDS = (
    "disease", "disease_subtype", "tissue", "cell_type",
    "disease_stage", "desired_phenotype", "organism",
)

CONFIDENCE = Literal["high", "medium", "low"]

LLM_SYSTEM_PROMPT = (
    "You convert a natural-language life-science research question into a structured",
    "JSON brief for a disease-to-target evidence review agent. Rules:",
    "1. Set a field only when the question explicitly or confidently supports it.",
    "2. Never invent tissue, cell type, disease stage or phenotype.",
    "3. disease: prefer the canonical disease name; do not invent a disease.",
    "4. field_confidence maps each set field to high/medium/low; empty fields are omitted.",
    "5. question_rewrite: keep the user intent, make it answerable, max 240 chars.",
    "6. constraints: list explicit user constraints; do not add policy.",
    "7. notes: only extraction uncertainties that a human reviewer must see.",
    "Return JSON only with keys: question_rewrite, disease, disease_subtype, tissue,",
    "cell_type, disease_stage, desired_phenotype, organism, constraints, notes, field_confidence.",
)


_SECRET_RE = re.compile(r"sk-[A-Za-z0-9]{20,}")


class QuestionNeedsInput(ValueError):
    """The question cannot be turned into a safe draft without user input."""


class ExtractedBrief(BaseModel):
    """Structured LLM extraction result; validation is only a syntax gate."""

    model_config = ConfigDict(extra="forbid")

    question_rewrite: str | None = None
    disease: str | None = None
    disease_subtype: str | None = None
    tissue: str | None = None
    cell_type: str | None = None
    disease_stage: str | None = None
    desired_phenotype: str | None = None
    organism: str | None = None
    constraints: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    field_confidence: dict[str, CONFIDENCE] = Field(default_factory=dict)


class QuestionDraft(BaseModel):
    """A reviewable draft: extracted fields, sources, notes and the spec."""

    model_config = ConfigDict(extra="forbid")

    draft_version: str = QUESTION_INTAKE_VERSION
    question: str = Field(min_length=3)
    disease_resolution: dict[str, Any]
    extracted: dict[str, str | None]
    confidence: dict[str, str]
    sources: dict[str, str]
    constraints: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(min_length=1)
    needs_review: bool = True
    spec: dict[str, Any]


def _detect_disease(question: str, library) -> tuple[DiseaseEntry, str] | None:
    """Longest curated match in the free text; ids and short ambiguous keys are skipped."""
    needle = (question or "").strip().casefold()
    if not needle:
        return None
    best: tuple[int, DiseaseEntry, str] | None = None
    for entry in library.diseases:
        for key in entry.lookup_keys():
            if not key or key == entry.id.casefold() or len(key) < 4:
                continue
            if re.search(r"\b" + re.escape(key) + r"\b", needle):
                if best is None or len(key) > best[0]:
                    best = (len(key), entry, key)
    if best is None:
        return None
    _, entry, key = best
    return entry, key


def _llm_brief(client: StepClient | None, question: str, hints: dict[str, Any]) -> ExtractedBrief | None:
    """Ask the model for a structured brief; None means unavailable or invalid."""
    if client is None:
        return None
    hint_lines = "\n".join(f"{key}={value}" for key, value in sorted(hints.items()) if value)
    user = f"Research question:\n{question}\n\nExplicit user hints (authoritative when present):\n{hint_lines or '(none)'}"
    try:
        payload = client.json_completion(LLM_SYSTEM_PROMPT, user)
        return ExtractedBrief.model_validate(payload)
    except (LLMUnavailable, ValidationError, ValueError):
        return None


def _merge_brief(
    question: str,
    hints: dict[str, Any],
    brief: ExtractedBrief | None,
    library,
) -> tuple[dict[str, str | None], dict[str, str], dict[str, str], list[str]]:
    """Merge hints > library detection > LLM > missing; returns fields/confidence/sources/notes."""
    fields: dict[str, str | None] = {name: None for name in BRIEF_FIELDS}
    confidence: dict[str, str] = {name: "missing" for name in BRIEF_FIELDS}
    sources: dict[str, str] = {name: "missing" for name in BRIEF_FIELDS}
    notes: list[str] = []

    def set_field(name: str, value: str | None, source: str, level: str) -> None:
        if value is None or not str(value).strip():
            return
        fields[name] = str(value).strip()
        confidence[name] = level
        sources[name] = source

    llm_values = brief.model_dump() if brief is not None else {}
    llm_confidence = llm_values.get("field_confidence") or {}
    llm_notes = list(llm_values.get("notes") or [])
    if brief is not None:
        for name in BRIEF_FIELDS:
            level = str(llm_confidence.get(name, "low"))
            set_field(name, llm_values.get(name), "llm", level)
    else:
        notes.append("llm_unavailable: only the curated disease match and explicit hints were used")

    detected = _detect_disease(question, library)
    if detected is not None:
        entry, matched_key = detected
        if fields.get("disease") and entry.name.casefold() != str(fields["disease"]).casefold():
            notes.append("curated disease match wins over LLM proposal: " + str(fields.get("disease")) + " -> " + entry.name)
        set_field("disease", entry.name, "library", "high")

    for name in BRIEF_FIELDS:
        hint_value = hints.get(name)
        if hint_value is not None and str(hint_value).strip():
            set_field(name, str(hint_value).strip(), "user", "high")

    if brief is not None and brief.question_rewrite:
        notes.append("question_rewrite: " + brief.question_rewrite)
    for note in llm_notes[:5]:
        notes.append("llm_note: " + note)
    return fields, confidence, sources, notes


def build_draft(
    question: str,
    *,
    hints: dict[str, Any] | None = None,
    client: StepClient | None = None,
    project_id: str | None = None,
    autonomy_mode: str = AutonomyMode.CHECKPOINTED.value,
    library_path: Path | None = None,
) -> QuestionDraft:
    """Build a reviewable draft project spec from a natural-language question.

    Raises QuestionNeedsInput when no disease can be established. The draft is
    never reserved or executed; callers must explicitly create the project.
    """
    question = (question or "").strip()
    if _SECRET_RE.search(question):
        raise QuestionNeedsInput("question contains a credential-like token; remove it before creating a project")
    if len(question) < 3:
        raise QuestionNeedsInput("question must be at least 3 characters")
    hints = {key: value for key, value in (hints or {}).items() if value not in (None, "")}
    library = load_library(library_path)
    brief = _llm_brief(client, question, hints)
    fields, confidence, sources, notes = _merge_brief(question, hints, brief, library)

    disease = fields.get("disease")
    if not disease:
        raise QuestionNeedsInput(
            "no disease could be established; add an explicit disease hint or rewrite the question"
        )

    resolution: dict[str, Any] = {"matched": False, "source": "free_text", "canonical_name": disease, "ontology_id": None}
    try:
        entry = library.find(disease)
        resolution = {
            "matched": True,
            "source": "library",
            "canonical_name": entry.name,
            "ontology_id": entry.ontology_id,
            "id": entry.id,
        }
        fields["disease"] = entry.name
        if sources["disease"] == "llm":
            sources["disease"] = "library"
        confidence["disease"] = "high"
        suggested = {
            "tissue": entry.context.tissue,
            "cell_type": entry.context.cell_type,
            "disease_stage": entry.context.disease_stage,
            "desired_phenotype": entry.context.desired_phenotype,
        }
        pending = {name: value for name, value in suggested.items() if value and not fields.get(name)}
        if pending:
            notes.append("library_context_suggestion (not injected): " + ", ".join(f"{k}={v}" for k, v in pending.items()))
        provided = [name for name, value in suggested.items() if value and fields.get(name)]
        if provided:
            notes.append("library context already covered by user/LLM fields: " + ", ".join(provided))
    except KeyError:
        notes.append("disease_not_in_curated_library: ontology id is not verified; add an explicit disease hint if this is a known disease")

    missing = [name for name, value in fields.items() if not value]
    low = [name for name, level in confidence.items() if level == "low" and fields.get(name)]
    if missing:
        notes.append("missing_context: " + ", ".join(missing) + " (keep missing or fill before creating)")
    if low:
        notes.append("low_confidence_fields: " + ", ".join(low))
    needs_review = bool(any(level != "high" for level in confidence.values())
                        or not resolution["matched"]
                        or brief is None)

    if not notes:
        notes.append("draft_ready: no unresolved extraction notes")

    constraints = list(dict.fromkeys([*(brief.constraints if brief else []), *hints.get("constraints", [])]))

    service = ResearchProjectService(ResearchProjectRuntime())
    spec = service.build_disease_project(
        question=question,
        disease=fields["disease"] or "",
        project_id=project_id,
        disease_subtype=fields.get("disease_subtype"),
        tissue=fields.get("tissue"),
        cell_type=fields.get("cell_type"),
        disease_stage=fields.get("disease_stage"),
        desired_phenotype=fields.get("desired_phenotype"),
        organism=fields.get("organism") or "Homo sapiens",
        autonomy_mode=autonomy_mode,
    )
    if brief is not None and brief.question_rewrite and brief.question_rewrite.strip() != question:
        goal = spec.goal.model_copy(update={"question": brief.question_rewrite.strip()})
        context = dict(spec.context)
        context["original_question"] = question
        spec = spec.model_copy(update={"goal": goal, "context": context})
    spec = spec.model_copy(update={"context": {**spec.context, "intake_draft_version": QUESTION_INTAKE_VERSION}})

    return QuestionDraft(
        question=question,
        disease_resolution=resolution,
        extracted=fields,
        confidence=confidence,
        sources=sources,
        constraints=constraints,
        review_notes=notes,
        needs_review=needs_review,
        spec=spec.model_dump(mode="json"),
    )


def reserve_draft(
    draft: QuestionDraft,
    settings,
) -> dict[str, Any]:
    """Reserve the draft as an immutable project; never executes it."""
    service = ResearchProjectService(ResearchProjectRuntime(settings=settings))
    return service.reserve(ResearchProjectSpec.model_validate(draft.spec))
