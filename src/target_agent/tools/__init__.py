"""Allowlisted scientific tool registry driven by a declarative enablement file."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..contracts import CONTRACT_VERSION, ToolDescriptor
from ..llm import StepClient
from ..settings import Settings, load_settings
from .base import ToolRegistry
from .literature import EuropePMCRAGTool
from .mch import MCHCausalGoldTool
from .omics import (
    BulkExpressionAnalysisTool, CellxgeneDiscoveryTool, DiseaseResolverTool,
    GEOMetadataAuditTool, GEOSearchTool, OmicsCandidateExtractionTool,
    OmicsRecipeBuilderTool, PathwayEnrichmentTool, SingleCellAnalysisTool,
)
from .opentargets import OpenTargetsTool
from .uc import DeltaFactorTool, ObservedTCellPerturbationTool, UCOmicsSnapshotTool


def _known_tools(settings: Settings) -> dict[str, object]:
    llm = StepClient.from_settings(settings)
    return {
        "disease_resolver": DiseaseResolverTool(),
        "geo_search": GEOSearchTool(),
        "geo_metadata_audit": GEOMetadataAuditTool(llm=llm),
        "omics_recipe_builder": OmicsRecipeBuilderTool(),
        "bulk_expression_analysis": BulkExpressionAnalysisTool(),
        "cellxgene_discovery": CellxgeneDiscoveryTool(),
        "single_cell_analysis": SingleCellAnalysisTool(),
        "pathway_enrichment": PathwayEnrichmentTool(),
        "omics_candidate_extraction": OmicsCandidateExtractionTool(),
        "open_targets": OpenTargetsTool(),
        "europe_pmc_rag": EuropePMCRAGTool(llm=llm),
        "uc_omics_snapshot": UCOmicsSnapshotTool(),
        "observed_tcell_perturbation": ObservedTCellPerturbationTool(),
        "deltafactor": DeltaFactorTool(),
        "mch_causal_gold": MCHCausalGoldTool(),
    }


def _config(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"tool registry config not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("tool registry contract version does not match runtime")
    return list(payload.get("tools") or [])


def default_registry(settings: Settings | None = None) -> ToolRegistry:
    settings = settings or load_settings()
    known = _known_tools(settings)
    configured = _config(settings.tool_registry_path)
    unknown = sorted({row.get("id") for row in configured} - set(known))
    if unknown:
        raise ValueError(f"tool registry contains unknown tools: {unknown}")
    tools = []
    for row in configured:
        if not row.get("enabled", False):
            continue
        tool = known[row["id"]]
        if hasattr(tool, "descriptor"):
            tool.descriptor = tool.descriptor.model_copy(update={"enabled": True})
        else:
            dimension = row.get("evidence_dimension") or ("causal_gold" if row["id"] == "mch_causal_gold" else "perturbation")
            tool.descriptor = ToolDescriptor(
                tool_id=row["id"], evidence_dimension=dimension,
                description=row.get("description") or row.get("validation_scope") or row["id"], enabled=True,
            )
        tools.append(tool)
    return ToolRegistry(tools)


__all__ = ["default_registry", "ToolRegistry"]
