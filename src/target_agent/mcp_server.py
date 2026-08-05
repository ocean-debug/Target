"""MCP adapter for the durable Target research product.

The adapter is intentionally thin: MCP is a transport for the same
ResearchProjectService used by local and HTTP clients, not a second Agent or a
second source of scientific state.
"""
from __future__ import annotations

import json
from typing import Any

from .research_runtime import ResearchProjectRuntime
from .research_service import ResearchProjectService


def create_mcp_server(
    service: ResearchProjectService | None = None,
    *,
    runtime: ResearchProjectRuntime | None = None,
):
    """Create the official-SDK MCP server without importing MCP at package load."""
    try:
        from mcp.server import MCPServer
    except ImportError as exc:  # pragma: no cover - exercised by CLI packaging smoke
        raise RuntimeError(
            "MCP support is not installed; install the project with the 'mcp' extra"
        ) from exc

    if service is not None and runtime is not None:
        raise ValueError("provide either service or runtime, not both")
    product = service or ResearchProjectService(runtime or ResearchProjectRuntime())
    server = MCPServer("TargetDiscovery")

    @server.tool()
    def target_capabilities() -> dict[str, Any]:
        """Describe Target's real project operations and explicit scientific boundaries."""
        return product.capabilities()

    @server.tool()
    def target_create_disease_project(
        question: str,
        disease: str,
        title: str | None = None,
        project_id: str | None = None,
        disease_subtype: str | None = None,
        tissue: str | None = None,
        cell_type: str | None = None,
        disease_stage: str | None = None,
        desired_phenotype: str | None = None,
        organism: str = "Homo sapiens",
        autonomy_mode: str = "checkpointed",
    ) -> dict[str, Any]:
        """Create an immutable disease-target project without starting execution.

        Omitted biological context is not inferred. Call target_run_project to
        advance the project until its next checkpoint or terminal state.
        """
        project = product.build_disease_project(
            question=question,
            disease=disease,
            title=title,
            project_id=project_id,
            disease_subtype=disease_subtype,
            tissue=tissue,
            cell_type=cell_type,
            disease_stage=disease_stage,
            desired_phenotype=desired_phenotype,
            organism=organism,
            autonomy_mode=autonomy_mode,
        )
        return product.reserve(project)

    @server.tool()
    def target_run_project(project_id: str) -> dict[str, Any]:
        """Advance a durable project until a checkpoint or terminal state."""
        return product.run(project_id)

    @server.tool()
    def target_get_project(project_id: str) -> dict[str, Any]:
        """Read the safe durable projection of a Target research project."""
        return product.snapshot(project_id)

    @server.tool()
    def target_list_projects() -> dict[str, Any]:
        """List available Target projects and their current durable status."""
        return {"projects": product.list_projects()}

    @server.tool()
    def target_get_events(project_id: str, after_sequence: int = 0) -> dict[str, Any]:
        """Replay ordered project events after a previously observed cursor."""
        events = product.events(project_id, after_sequence=after_sequence)
        return {
            "project_id": project_id,
            "events": events,
            "next_cursor": events[-1]["sequence"] if events else after_sequence,
        }

    @server.tool()
    def target_get_domain_activities(
        project_id: str,
        after_sequence: int = 0,
        limit: int = 200,
        work_item_id: str | None = None,
    ) -> dict[str, Any]:
        """Read source-linked domain stages without copying scientific results."""
        return product.domain_activities(
            project_id,
            after_sequence=after_sequence,
            limit=limit,
            work_item_id=work_item_id,
        )

    @server.tool()
    def target_get_repairs(project_id: str) -> dict[str, Any]:
        """Read immutable repair requests, execution overlays and verified outcomes."""
        return product.repairs(project_id)

    @server.tool()
    def target_decide_repair(
        project_id: str,
        repair_request_id: str,
        trigger_snapshot_digest: str,
        approve: bool,
        actor: str,
        rationale: str,
        resume: bool = True,
    ) -> dict[str, Any]:
        """Approve or reject one exact repair snapshot; stale digests are refused."""
        return product.decide_repair(
            project_id=project_id,
            repair_request_id=repair_request_id,
            trigger_snapshot_digest=trigger_snapshot_digest,
            approve=approve,
            actor=actor,
            rationale=rationale,
            resume=resume,
        )

    @server.tool()
    def target_accept_checkpoint(
        project_id: str,
        target_id: str,
        actor: str,
        rationale: str,
        resume: bool = True,
    ) -> dict[str, Any]:
        """Accept a frozen plan, supervised work item or exact release gate."""
        return product.accept_checkpoint(
            project_id=project_id,
            target_id=target_id,
            actor=actor,
            rationale=rationale,
            resume=resume,
        )

    @server.tool()
    def target_read_text_artifact(
        project_id: str,
        artifact_id: str,
        max_characters: int = 100_000,
    ) -> dict[str, Any]:
        """Read a checksum-verified text artifact under an explicit size bound."""
        return product.read_text_artifact(
            project_id,
            artifact_id,
            max_characters=max_characters,
        )

    @server.resource("target://projects/{project_id}")
    def target_project_resource(project_id: str) -> str:
        """Return one durable project as a JSON resource."""
        return json.dumps(product.snapshot(project_id), ensure_ascii=False, indent=2)

    @server.resource("target://projects/{project_id}/artifacts/{artifact_id}")
    def target_artifact_resource(project_id: str, artifact_id: str) -> str:
        """Return one verified text artifact as a JSON resource."""
        return json.dumps(
            product.read_text_artifact(project_id, artifact_id),
            ensure_ascii=False,
            indent=2,
        )

    return server


def main() -> None:
    """Run Target as a local stdio MCP server."""
    create_mcp_server().run(transport="stdio")


__all__ = ["create_mcp_server", "main"]


if __name__ == "__main__":  # pragma: no cover
    main()
