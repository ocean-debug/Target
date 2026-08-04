"""Curated disease library: ontology-verified entries plus benchmark task templates.

Each entry carries an OLS-verified ontology identifier (MONDO/EFO), evidence-graded
reference targets for ranking sanity checks, and a default biological context.
Task templates follow the 50/20/15/15 composition from the project task book:
normal / missing_context / conflicting_evidence / trap.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from .contracts import TaskContext, TaskSpec
from .settings import PROJECT_ROOT

LIBRARY_PATH = PROJECT_ROOT / "configs" / "disease_library.yaml"

EVIDENCE_LEVELS = ("approved_drug", "gwas", "mendelian", "clinical_trial", "mechanistic")
TEMPLATE_KINDS = ("normal", "missing_context", "conflicting_evidence", "trap")

_ONTOLOGY_RE = re.compile(r"^(MONDO|EFO)[:_]\d{7}$")

DEFAULT_REQUESTED_OUTPUTS = [
    "ranked_targets",
    "highlighted_targets",
    "target_cards",
    "experiment_plans",
    "traceable_report",
]


def _ontology_underscore(ontology_id: str) -> str:
    """Canonical in-pipeline form uses underscores (MONDO_0005101)."""
    return ontology_id.replace(":", "_")


class ReferenceTarget(BaseModel):
    gene: str
    evidence: Literal["approved_drug", "gwas", "mendelian", "clinical_trial", "mechanistic"]
    note: str = ""
    alt_symbols: list[str] = Field(default_factory=list)


class DiseaseContext(BaseModel):
    organism: str = "Homo sapiens"
    tissue: str | None = None
    cell_type: str | None = None
    disease_stage: str | None = None
    desired_phenotype: str | None = None


class DiseaseEntry(BaseModel):
    id: str
    name: str
    name_zh: str = ""
    ontology_id: str
    category: str
    synonyms: list[str] = Field(default_factory=list)
    context: DiseaseContext = Field(default_factory=DiseaseContext)
    reference_targets: list[ReferenceTarget] = Field(min_length=2)

    @model_validator(mode="after")
    def check_ontology_id(self) -> "DiseaseEntry":
        if not _ONTOLOGY_RE.match(self.ontology_id):
            raise ValueError(f"{self.id}: ontology_id {self.ontology_id!r} is not a MONDO/EFO CURIE")
        return self

    def lookup_keys(self) -> set[str]:
        keys = {self.id.casefold(), self.name.casefold(), self.name_zh.casefold()}
        keys.update(s.casefold() for s in self.synonyms)
        return {k for k in keys if k}

    def to_task_spec(self, kind: Literal["normal", "missing_context", "conflicting_evidence", "trap"] = "normal",
                     template: "TaskTemplate | None" = None, **overrides: Any) -> TaskSpec:
        """Render a benchmark-ready TaskSpec from this entry and a task template."""
        if kind not in TEMPLATE_KINDS:
            raise ValueError(f"unknown template kind {kind!r}; expected one of {TEMPLATE_KINDS}")
        context_fields: dict[str, Any] = {
            "disease": self.name,
            "disease_id": _ontology_underscore(self.ontology_id),
            "organism": self.context.organism,
            "tissue": self.context.tissue,
            "cell_type": self.context.cell_type,
            "disease_stage": self.context.disease_stage,
            "desired_phenotype": self.context.desired_phenotype,
        }
        question = overrides.pop("question", None)
        if template is not None:
            question = template.question
            for field, value in template.context_overrides.items():
                if field in context_fields:
                    context_fields[field] = value
        if question is None:
            question = f"Discover traceable targets for {self.name}"
        question = question.format(
            name=self.name,
            tissue=context_fields.get("tissue") or "disease-relevant tissue",
            cell_type=context_fields.get("cell_type") or "disease-relevant cell type",
        )
        context_fields.update(overrides.pop("context", {}))
        return TaskSpec(
            task_type="disease_to_target",
            question=question,
            context=TaskContext(**context_fields),
            requested_outputs=list(overrides.pop("requested_outputs", DEFAULT_REQUESTED_OUTPUTS)),
            **overrides,
        )


class TaskTemplate(BaseModel):
    weight: float = Field(gt=0, le=1)
    question: str = Field(min_length=3)
    context_overrides: dict[str, Any] = Field(default_factory=dict)
    expectation: dict[str, Any] = Field(default_factory=dict)


class DiseaseLibrary(BaseModel):
    version: str
    diseases: list[DiseaseEntry] = Field(min_length=1)
    task_templates: dict[str, TaskTemplate] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_unique_ids(self) -> "DiseaseLibrary":
        ids = [d.id for d in self.diseases]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate disease ids in library")
        unknown = set(self.task_templates) - set(TEMPLATE_KINDS)
        if unknown:
            raise ValueError(f"unknown task template kinds: {sorted(unknown)}")
        return self

    def find(self, query: str) -> DiseaseEntry:
        """Case-insensitive lookup by id, English/Chinese name, or any synonym."""
        needle = (query or "").strip().casefold()
        if not needle:
            raise KeyError(f"empty disease query; available ids: {self.ids()}")
        for entry in self.diseases:
            if needle in entry.lookup_keys():
                return entry
        raise KeyError(f"disease {query!r} not in library; available ids: {self.ids()}")

    def ids(self) -> list[str]:
        return [d.id for d in self.diseases]

    def template(self, kind: str) -> TaskTemplate:
        try:
            return self.task_templates[kind]
        except KeyError:
            raise KeyError(f"template {kind!r} not defined; available: {sorted(self.task_templates)}") from None

    def resolver_aliases(self) -> dict[str, tuple[str, list[str], str]]:
        """Alias map in DiseaseResolverTool.ALIASES shape: key -> (name, synonyms, MONDO_xxx)."""
        aliases: dict[str, tuple[str, list[str], str]] = {}
        for entry in self.diseases:
            synonyms = list(dict.fromkeys([entry.name, *entry.synonyms]))
            value = (entry.name, synonyms, _ontology_underscore(entry.ontology_id))
            for key in entry.lookup_keys():
                aliases.setdefault(key, value)
        return aliases

    def to_task_spec(self, query: str,
                     kind: Literal["normal", "missing_context", "conflicting_evidence", "trap"] = "normal",
                     **overrides: Any) -> TaskSpec:
        entry = self.find(query)
        return entry.to_task_spec(kind=kind, template=self.task_templates.get(kind), **overrides)


@lru_cache(maxsize=4)
def _load_cached(path_str: str) -> DiseaseLibrary:
    payload = yaml.safe_load(Path(path_str).read_text(encoding="utf-8"))
    return DiseaseLibrary.model_validate(payload)


def load_library(path: Path | None = None) -> DiseaseLibrary:
    """Load and validate the curated disease library (cached)."""
    return _load_cached(str(path or LIBRARY_PATH))
