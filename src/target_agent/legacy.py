"""Explicit one-way adapters into the current 2.1.0 contracts."""
from __future__ import annotations

from typing import Any

from .contracts import (
    ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, SourceLocator,
    TaskSpec, ToolCapability, ToolResult, ToolStatus,
)


LEGACY_VERSIONS = {"1.0.0", "1.1.0", "1.0", "1.1"}
V2_CONTRACT_VERSION = "2.0.0"


def adapt_task_spec_2_0(payload: dict[str, Any]) -> TaskSpec:
    """Explicitly migrate one 2.0 TaskSpec before it enters a 2.1 run."""
    if payload.get("contract_version") != V2_CONTRACT_VERSION:
        raise ValueError("only a 2.0.0 TaskSpec can use the 2.0-to-2.1 adapter")

    def migrate(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: ("2.1.0" if key == "contract_version" and item == V2_CONTRACT_VERSION else migrate(item)) for key, item in value.items()}
        if isinstance(value, list):
            return [migrate(item) for item in value]
        return value

    return TaskSpec.model_validate(migrate(payload))


def _assert_legacy(payload: dict[str, Any]) -> None:
    version = str(payload.get("contract_version") or payload.get("schema_version") or "")
    if version not in LEGACY_VERSIONS:
        raise ValueError(f"unsupported legacy contract version: {version or 'missing'}")


def adapt_evidence(payload: dict[str, Any], tool_run_id: str | None = None) -> EvidenceItem:
    _assert_legacy(payload)
    class_map = {
        "literature": ClaimClass.FACT,
        "measured": ClaimClass.OBSERVED,
        "model_prediction": ClaimClass.PREDICTED,
        "team_inference": ClaimClass.INFERRED,
    }
    uri = str(payload.get("source_uri") or "")
    statement = str(payload.get("claim") or "")
    run_id = tool_run_id or payload.get("tool_run_id")
    if not run_id:
        raise ValueError("legacy evidence cannot migrate without tool_run_id")
    if not uri or not statement:
        raise ValueError("legacy evidence requires source_uri and claim")
    legacy_context = payload.get("context") or {}
    return EvidenceItem(
        tool_run_id=run_id,
        gene_symbol=payload.get("gene_symbol"),
        claim_class=class_map[str(payload.get("evidence_class"))],
        statement=statement,
        source=SourceLocator(uri=uri, source_id=uri, version=payload.get("contract_version")),
        source_span=str(payload.get("source_span") or statement),
        context=EvidenceContext(
            organism=legacy_context.get("organism"),
            tissue=legacy_context.get("tissue"),
            cell_type=legacy_context.get("cell_type") or legacy_context.get("celltype"),
            disease=payload.get("disease"),
            assay=legacy_context.get("assay") or legacy_context.get("method"),
        ),
        stance=payload.get("stance", "uncertain"),
        effect=payload.get("effect") or {},
        uncertainty="Migrated legacy evidence; source span was not independently revalidated.",
        quality_flags=[*(payload.get("quality_flags") or []), "legacy_contract_migrated"],
        context_match_score=float(payload.get("context_match_score") or 0.5),
    )


def adapt_tool_result(payload: dict[str, Any]) -> ToolResult:
    _assert_legacy(payload)
    outputs = payload.get("outputs") or {}
    covered = outputs.get("covered", True)
    ok = bool(payload.get("ok", False))
    if not ok:
        status, coverage = ToolStatus.FAILED, CoverageStatus.UNKNOWN
    elif not covered:
        status, coverage = ToolStatus.OUT_OF_SCOPE, CoverageStatus.NOT_COVERED
    else:
        status, coverage = ToolStatus.SUCCESS, CoverageStatus.COVERED
    return ToolResult(
        tool_run_id=str(payload.get("tool_run_id") or ""),
        tool_name=str(payload.get("tool_name") or "legacy_tool"),
        tool_version=str(payload.get("tool_version") or "legacy"),
        status=status,
        coverage_status=coverage,
        context_match_score=float(payload.get("context_match_score") or (1.0 if covered else 0.0)),
        inputs=payload.get("inputs") or {},
        outputs=outputs,
        capability=ToolCapability(validation_scope="Migrated from legacy contract; capability unknown."),
        warnings=payload.get("quality_flags") or [],
        limitations=["Legacy tool result migrated; provenance may be incomplete."],
        error=payload.get("error") if not ok else None,
        cached=bool(payload.get("cached", False)),
        elapsed_ms=int(payload.get("elapsed_ms") or 0),
    )


def reject_mixed_versions(payloads: list[dict[str, Any]]) -> None:
    versions = {str(p.get("contract_version") or p.get("schema_version")) for p in payloads}
    if len(versions) > 1:
        raise ValueError(f"mixed contract versions in one run: {sorted(versions)}")
