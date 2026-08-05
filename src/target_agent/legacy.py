"""Explicit one-way adapters into the current 2.2.0 contracts."""
from __future__ import annotations

from typing import Any

from .contracts import (
    CONTRACT_VERSION, ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, SourceLocator,
    TaskSpec, ToolCapability, ToolResult, ToolStatus,
)


LEGACY_VERSIONS = {"1.0.0", "1.1.0", "1.0", "1.1"}
V2_CONTRACT_VERSION = "2.0.0"
V21_CONTRACT_VERSION = "2.1.0"


def migrate_current_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate or migrate one homogeneous 2.0/2.1/current payload tree."""
    root_version = payload.get("contract_version")
    if root_version not in {CONTRACT_VERSION, V2_CONTRACT_VERSION, V21_CONTRACT_VERSION}:
        raise ValueError(f"unsupported contract version: {root_version or 'missing'}")
    discovered: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if "contract_version" in value:
                discovered.add(str(value["contract_version"]))
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(payload)
    if discovered - {str(root_version)}:
        raise ValueError(f"mixed contract versions in one payload: {sorted(discovered)}")
    if root_version == CONTRACT_VERSION:
        return payload

    def migrate(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: (CONTRACT_VERSION if key == "contract_version" else migrate(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [migrate(item) for item in value]
        return value

    return migrate(payload)


def parse_task_spec(payload: dict[str, Any]) -> TaskSpec:
    return TaskSpec.model_validate(migrate_current_contract(payload))


def _migrate_task_payload(payload: dict[str, Any], source_version: str) -> TaskSpec:
    if payload.get("contract_version") != source_version:
        raise ValueError(f"only a {source_version} TaskSpec can use this adapter")

    return parse_task_spec(payload)


def adapt_task_spec_2_0(payload: dict[str, Any]) -> TaskSpec:
    """Explicitly migrate one 2.0 TaskSpec before it enters a 2.2 run."""
    return _migrate_task_payload(payload, V2_CONTRACT_VERSION)


def adapt_task_spec_2_1(payload: dict[str, Any]) -> TaskSpec:
    """Explicitly migrate one 2.1 TaskSpec before it enters a 2.2 run."""
    return _migrate_task_payload(payload, V21_CONTRACT_VERSION)


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
