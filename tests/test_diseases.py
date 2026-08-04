"""Disease library: validation, lookup, task-spec rendering and resolver merge."""
from __future__ import annotations

import re

import pytest

from target_agent.contracts import TaskSpec
from target_agent.diseases import TEMPLATE_KINDS, load_library
from target_agent.tools.omics import DiseaseResolverTool


@pytest.fixture(scope="module")
def library():
    return load_library()


def test_library_loads_and_ids_unique(library):
    ids = library.ids()
    assert len(ids) == len(set(ids))
    assert len(ids) >= 15


def test_ontology_ids_are_valid_curies(library):
    pattern = re.compile(r"^(MONDO|EFO):\d{7}$")
    for entry in library.diseases:
        assert pattern.match(entry.ontology_id), entry.id


def test_reference_targets_have_graded_evidence(library):
    allowed = {"approved_drug", "gwas", "mendelian", "clinical_trial", "mechanistic"}
    gene_pattern = re.compile(r"^[A-Z0-9][A-Za-z0-9.-]*$")  # HGNC-style, e.g. C9orf72
    for entry in library.diseases:
        assert len(entry.reference_targets) >= 2, entry.id
        for target in entry.reference_targets:
            assert target.evidence in allowed
            assert gene_pattern.match(target.gene), f"{entry.id}: {target.gene}"


def test_find_by_id_english_chinese_synonym(library):
    uc = library.find("uc")
    assert uc is library.find("UC")
    assert uc is library.find("ulcerative colitis")
    assert uc is library.find("溃疡性结肠炎")
    assert uc.ontology_id == "MONDO:0005101"
    with pytest.raises(KeyError, match="available ids"):
        library.find("not-a-disease")


def test_normal_task_spec_is_valid_and_uses_default_context(library):
    task = library.to_task_spec("uc", kind="normal")
    assert isinstance(task, TaskSpec)
    assert task.task_type == "disease_to_target"
    assert task.context.disease == "ulcerative colitis"
    assert task.context.disease_id == "MONDO_0005101"  # in-pipeline underscore form
    assert task.context.tissue == "rectum"
    assert task.context.cell_type == "T cell"
    assert "ulcerative colitis" in task.question
    assert task.requested_outputs


def test_missing_context_template_blanks_tissue_and_cell_type(library):
    task = library.to_task_spec("ra", kind="missing_context")
    assert task.context.tissue is None
    assert task.context.cell_type is None
    assert task.context.disease  # scope validator still satisfied
    assert "rheumatoid arthritis" in task.question


def test_all_four_template_buckets_render_for_every_disease(library):
    assert set(library.task_templates) == set(TEMPLATE_KINDS)
    for entry in library.diseases:
        for kind in TEMPLATE_KINDS:
            task = entry.to_task_spec(kind=kind, template=library.task_templates[kind])
            assert task.question.strip()


def test_template_expectations_are_machine_checkable(library):
    for kind, template in library.task_templates.items():
        assert 0 < template.weight <= 1
        statuses = template.expectation.get("terminal_status_in")
        assert statuses, kind
        assert set(statuses) <= {"completed", "completed_with_gaps", "needs_input", "refused", "failed"}


def test_resolver_merges_library_aliases(library):
    aliases = DiseaseResolverTool.aliases()
    assert aliases["uc"][2] == "MONDO_0005101"
    assert aliases["溃疡性结肠炎"][0] == "ulcerative colitis"
    assert "nash" in aliases and "慢阻肺" in aliases
    # hard-coded legacy aliases still win on conflict
    assert aliases["ulcerative colitis"][1] == ["ulcerative colitis", "UC", "inflammatory bowel disease"]
