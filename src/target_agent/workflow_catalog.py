"""Executable workflow templates for the Target research product.

A workflow template is the product-level unit that lets Target carry different
scientific questions from intake to a reviewed report.  Every template is a
typed YAML document in the workflows/ directory; the planner and the project
runtime consume the template, so workflows/*.yaml are contracts rather than
documentation.  A project freezes the template id and its source SHA-256; if
the template file changes after the project is created, the runtime fails
closed instead of silently executing a different workflow.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import ConfigDict, Field, model_validator

from .research_contracts import ResearchContract
from .settings import load_settings


class WorkflowModuleSpec(ResearchContract):
    """One typed module the template may execute."""

    model_config = ConfigDict(extra="forbid")

    module: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    required: bool = False
    dependencies: list[str] = Field(default_factory=list)
    input_contract: str | None = None
    objective: str | None = None
    max_attempts: int = Field(default=1, ge=1, le=3)


class WorkflowTemplate(ResearchContract):
    """Executable workflow contract loaded from workflows/*.yaml."""

    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=3)
    product: str = Field(default="target_discovery_agent", min_length=1)
    domain: str = Field(default="life_science", pattern="^(disease_target_discovery|life_science)$")
    task_types: list[str] = Field(default_factory=list)
    modules: list[WorkflowModuleSpec] = Field(min_length=1)
    max_work_items: int = Field(default=12, ge=1, le=30)
    human_checkpoints: dict[str, list[str]] = Field(default_factory=dict)
    contract_version: str = Field(default="1.0.0", min_length=1)
    source_sha256: str = Field(default="")

    @model_validator(mode="after")
    def validate_module_graph(self) -> "WorkflowTemplate":
        names = [item.module for item in self.modules]
        if len(names) != len(set(names)):
            raise ValueError("workflow template modules must be unique")
        known = set(names)
        for item in self.modules:
            unknown = set(item.dependencies) - known
            if unknown:
                raise ValueError(
                    f"workflow module {item.module} has unknown dependencies: {sorted(unknown)}"
                )
            if item.module in item.dependencies:
                raise ValueError(f"workflow module {item.module} cannot depend on itself")
        visiting: set[str] = set()
        visited: set[str] = set()
        edges = {item.module: item.dependencies for item in self.modules}

        def visit(module: str) -> None:
            if module in visiting:
                raise ValueError("workflow template contains a dependency cycle")
            if module in visited:
                return
            visiting.add(module)
            for dependency in edges[module]:
                visit(dependency)
            visiting.remove(module)
            visited.add(module)

        for module in names:
            visit(module)
        if not any(item.required for item in self.modules):
            raise ValueError("workflow template must declare at least one required module")
        return self


class WorkflowCatalogError(ValueError):
    """Raised when the workflow catalog cannot be loaded or a template is invalid."""


class WorkflowCatalog:
    """Deterministic, checksum-bound loader for executable workflow templates."""

    def __init__(self, workflows_dir: Path | str | None = None):
        self.workflows_dir = (
            Path(workflows_dir) if workflows_dir else load_settings().workflow_catalog_path
        )
        self._templates: dict[str, WorkflowTemplate] | None = None

    def _load(self) -> dict[str, WorkflowTemplate]:
        if self._templates is not None:
            return self._templates
        if not self.workflows_dir.is_dir():
            raise WorkflowCatalogError(f"workflow catalog directory not found: {self.workflows_dir}")
        templates: dict[str, WorkflowTemplate] = {}
        for path in sorted(self.workflows_dir.glob("*.yaml")):
            raw = path.read_text(encoding="utf-8")
            try:
                data = yaml.safe_load(raw)
            except yaml.YAMLError as exc:
                raise WorkflowCatalogError(f"invalid YAML in {path.name}: {exc}") from exc
            if not isinstance(data, dict) or not data.get("template_id"):
                # Legacy descriptive documents are not executable templates.
                continue
            data = dict(data)
            data["source_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            try:
                template = WorkflowTemplate.model_validate(data)
            except Exception as exc:
                raise WorkflowCatalogError(f"invalid workflow template {path.name}: {exc}") from exc
            if template.template_id in templates:
                raise WorkflowCatalogError(
                    f"duplicate workflow template id: {template.template_id}"
                )
            templates[template.template_id] = template
        self._templates = templates
        return templates

    def list_templates(self) -> list[WorkflowTemplate]:
        return sorted(self._load().values(), key=lambda item: item.template_id)

    def get(self, template_id: str) -> WorkflowTemplate:
        templates = self._load()
        if template_id not in templates:
            raise WorkflowCatalogError(
                f"unknown workflow template: {template_id}; available: {sorted(templates)}"
            )
        return templates[template_id]

    def required_modules(self, template_id: str) -> list[str]:
        template = self.get(template_id)
        return [item.module for item in template.modules if item.required]

    def allowed_modules(self, template_id: str) -> set[str]:
        template = self.get(template_id)
        return {item.module for item in template.modules}

    def module_specs(self, template_id: str) -> dict[str, WorkflowModuleSpec]:
        template = self.get(template_id)
        return {item.module: item for item in template.modules}

    def validate_plan_modules(
        self, template_id: str, plan_modules: list[str]
    ) -> None:
        """Reject plans that leave the template allowlist or drop required modules."""
        template = self.get(template_id)
        allowed = {item.module for item in template.modules}
        unknown = set(plan_modules) - allowed
        if unknown:
            raise WorkflowCatalogError(
                f"plan uses modules outside template {template_id}: {sorted(unknown)}"
            )
        missing = {item.module for item in template.modules if item.required} - set(plan_modules)
        if missing:
            raise WorkflowCatalogError(
                f"plan omits required template modules: {sorted(missing)}"
            )
        for item in template.modules:
            if item.required and plan_modules.count(item.module) != 1:
                raise WorkflowCatalogError(
                    f"required template module must appear exactly once: {item.module}"
                )
        if len(plan_modules) > template.max_work_items:
            raise WorkflowCatalogError(
                f"plan exceeds template {template.template_id} max_work_items "
                f"({len(plan_modules)} > {template.max_work_items})"
            )


__all__ = [
    "WorkflowCatalog",
    "WorkflowCatalogError",
    "WorkflowModuleSpec",
    "WorkflowTemplate",
]