"""Application service for durable Target research projects.

The HTTP workbench, CLI and MCP adapter should operate on this service rather
than inventing separate project semantics.  It exposes only durable project
records and never returns deployment paths or credentials.
"""
from __future__ import annotations

from typing import Any

from .contracts import TaskContext, TaskSpec
from .research_contracts import (
    RESEARCH_CONTRACT_VERSION,
    AutonomyMode,
    DecisionAction,
    DecisionEvent,
    ProjectStatus,
    ResearchGoal,
    ResearchProjectSpec,
)
from .research_runtime import ResearchProjectRuntime
from .research_store import ResearchProjectStore


_TERMINAL_PROJECT_STATUSES = {
    ProjectStatus.COMPLETED,
    ProjectStatus.COMPLETED_WITH_GAPS,
    ProjectStatus.FAILED,
    ProjectStatus.CANCELLED,
}


class ResearchProjectNotFound(ValueError):
    """Raised when a requested durable project does not exist."""


class ResearchDecisionError(ValueError):
    """Raised when a checkpoint decision is not part of the frozen plan."""


class ResearchProjectService:
    """Stable product-facing operations over the research runtime and store."""

    def __init__(self, runtime: ResearchProjectRuntime):
        self.runtime = runtime
        self.projects_dir = runtime.projects_dir

    def build_disease_project(
        self,
        *,
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
        autonomy_mode: str = AutonomyMode.CHECKPOINTED.value,
    ) -> ResearchProjectSpec:
        """Build the typed minimum intake for a public-data target project.

        Missing biological context is preserved as missing.  The downstream
        workflow may request it or complete with gaps; this helper never infers
        tissue, cell type, disease stage or phenotype from prose.
        """
        mode = AutonomyMode(autonomy_mode)
        target_task = TaskSpec(
            task_type="disease_to_target",
            question=question,
            context=TaskContext(
                disease=disease,
                disease_subtype=disease_subtype,
                organism=organism,
                tissue=tissue,
                cell_type=cell_type,
                disease_stage=disease_stage,
                desired_phenotype=desired_phenotype,
            ),
            requested_outputs=[
                "ranked_targets",
                "target_cards",
                "falsifiable_experiment_plans",
                "traceable_research_report",
            ],
        )
        values: dict[str, Any] = {
            "title": title or f"Target research: {disease}",
            "domain": "disease_target_discovery",
            "goal": ResearchGoal(
                question=question,
                success_criteria=[
                    "Every material conclusion traces to a source or reproducible tool result.",
                    "Candidate ranking preserves supporting, opposing and missing evidence separately.",
                    "Priority targets include falsifiable experiments and explicit scientific boundaries.",
                ],
                deliverables=[
                    "Ranked target list",
                    "TargetCards",
                    "Falsifiable experiment plans",
                    "Machine-readable evidence package",
                    "Human-readable research report",
                ],
                constraints=[
                    "Use public data only unless a later immutable project explicitly changes this constraint.",
                    "Do not represent retrieval, association or model prediction as causal biological truth.",
                ],
            ),
            "context": {"target_task_spec": target_task.model_dump(mode="json")},
            "autonomy_mode": mode,
        }
        if project_id:
            values["project_id"] = project_id
        return ResearchProjectSpec.model_validate(values)

    def reserve(self, project: ResearchProjectSpec) -> dict[str, Any]:
        """Persist an immutable project specification without executing it."""
        store = self._store(project.project_id)
        created = store.create(project)
        return {
            "created": created,
            "project": self.snapshot(project.project_id),
        }

    def run(self, project_id: str) -> dict[str, Any]:
        """Advance a project until its next terminal state or human checkpoint."""
        store = self._existing_store(project_id)
        project = store.load_spec()
        assert project is not None
        state = store.load_state()
        resume = state is not None
        self.runtime.run(project, resume=resume)
        return self.snapshot(project_id)

    def accept_checkpoint(
        self,
        *,
        project_id: str,
        target_id: str,
        actor: str,
        rationale: str,
        resume: bool = False,
    ) -> dict[str, Any]:
        """Accept a frozen plan, supervised item or release gate.

        The accepted target must already exist in the immutable plan.  This is
        intentionally narrower than a generic decision API because the current
        runtime does not yet execute project-level reject/replan semantics.
        """
        if not actor.strip() or not rationale.strip():
            raise ResearchDecisionError("actor and rationale are required")
        store = self._existing_store(project_id)
        project, plan = store.load_spec(), store.load_plan()
        if project is None or plan is None:
            raise ResearchDecisionError("project does not yet have a frozen plan")
        allowed = {plan.plan_id, *(item.item_id for item in plan.items), f"release:{plan.plan_id}"}
        if target_id not in allowed:
            raise ResearchDecisionError("decision target is not part of the frozen project plan")
        decision = next(
            (
                row
                for row in store.read_decisions()
                if row.action == DecisionAction.ACCEPT and target_id in row.target_ids
            ),
            None,
        )
        if decision is None:
            decision = DecisionEvent(
                project_id=project_id,
                action=DecisionAction.ACCEPT,
                target_ids=[target_id],
                actor=actor.strip(),
                rationale=rationale.strip(),
                reversible=False,
            )
            store.append_decision(decision)
        if resume:
            self.runtime.run(project, resume=True)
        return {
            "decision": decision.model_dump(mode="json"),
            "project": self.snapshot(project_id),
        }

    def list_projects(self) -> list[dict[str, Any]]:
        """List durable project summaries without exposing filesystem paths."""
        if not self.projects_dir.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self.projects_dir.iterdir(), key=lambda item: item.name):
            if not path.is_dir():
                continue
            try:
                store = self._store(path.name)
                spec = store.load_spec()
                if spec is None:
                    continue
                state = store.load_state()
            except ValueError:
                continue
            rows.append(
                {
                    "project_id": spec.project_id,
                    "title": spec.title,
                    "domain": spec.domain,
                    "status": state.status.value if state else ProjectStatus.DRAFT.value,
                    "updated_at": state.updated_at if state else spec.created_at,
                }
            )
        return rows

    def snapshot(self, project_id: str) -> dict[str, Any]:
        """Return the complete safe control-plane projection for one project."""
        store = self._existing_store(project_id)
        spec = store.load_spec()
        assert spec is not None
        state = store.load_state()
        plan = store.load_plan()
        results = store.load_work_item_results()
        events = store.read_events()
        return {
            "contract_version": RESEARCH_CONTRACT_VERSION,
            "spec": spec.model_dump(mode="json"),
            "state": state.model_dump(mode="json") if state else None,
            "plan": plan.model_dump(mode="json") if plan else None,
            "work_item_results": [results[key].model_dump(mode="json") for key in sorted(results)],
            "artifacts": [row.model_dump(mode="json") for row in store.read_artifacts()],
            "assessments": [row.model_dump(mode="json") for row in store.read_assessments()],
            "decisions": [row.model_dump(mode="json") for row in store.read_decisions()],
            "event_cursor": events[-1].sequence if events else 0,
            "next_actions": self._next_actions(store),
        }

    def events(self, project_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        """Read replayable ordered events after a client cursor."""
        if after_sequence < 0:
            raise ValueError("after_sequence must be non-negative")
        store = self._existing_store(project_id)
        return [
            row.model_dump(mode="json")
            for row in store.read_events()
            if row.sequence > after_sequence
        ]

    def read_text_artifact(
        self, project_id: str, artifact_id: str, max_characters: int = 100_000,
    ) -> dict[str, Any]:
        """Read a verified text artifact with an explicit context-size bound."""
        if max_characters < 1 or max_characters > 1_000_000:
            raise ValueError("max_characters must be between 1 and 1000000")
        store = self._existing_store(project_id)
        record = next((row for row in store.read_artifacts() if row.artifact_id == artifact_id), None)
        if record is None:
            raise ResearchProjectNotFound(f"artifact not found: {artifact_id}")
        store.assert_integrity()
        path = store.artifact_path(record)
        textual = record.media_type.startswith("text/") or record.media_type in {
            "application/json",
            "application/x-ndjson",
        }
        payload: dict[str, Any] = {"artifact": record.model_dump(mode="json")}
        if not textual:
            return {**payload, "content": None, "truncated": False, "reason": "binary_artifact"}
        content = path.read_text(encoding="utf-8")
        return {
            **payload,
            "content": content[:max_characters],
            "truncated": len(content) > max_characters,
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "research_contract_version": RESEARCH_CONTRACT_VERSION,
            "domain": "disease_target_discovery",
            "operations": [
                "create_disease_project",
                "run_project",
                "get_project",
                "list_projects",
                "get_events",
                "accept_checkpoint",
                "read_text_artifact",
            ],
            "autonomy_modes": [mode.value for mode in AutonomyMode],
            "module_capabilities": self.runtime.registry.public_capabilities(),
            "boundaries": [
                "No arbitrary model-generated code or shell execution is exposed by this service.",
                "Missing biological context remains missing and may require user input.",
                "MCP/HTTP clients receive durable projections, not filesystem deployment paths.",
            ],
        }

    def _next_actions(self, store: ResearchProjectStore) -> list[dict[str, Any]]:
        spec, state, plan = store.load_spec(), store.load_state(), store.load_plan()
        if spec is None:
            return []
        if state is None:
            return [{"action": "run_project", "project_id": spec.project_id}]
        accepted = {
            target_id
            for row in store.read_decisions()
            if row.action == DecisionAction.ACCEPT
            for target_id in row.target_ids
        }
        if plan is not None and plan.plan_id not in accepted and state.status == ProjectStatus.NEEDS_INPUT:
            return [{
                "action": "accept_checkpoint",
                "target_id": plan.plan_id,
                "reason": "The frozen plan requires human acceptance.",
            }]
        if state.status == ProjectStatus.NEEDS_INPUT and state.current_item_id:
            return [{
                "action": "accept_checkpoint",
                "target_id": state.current_item_id,
                "reason": "The supervised work item requires human acceptance or additional input.",
            }]
        if state.status == ProjectStatus.WAITING_REVIEW and plan is not None:
            return [{
                "action": "accept_checkpoint",
                "target_id": f"release:{plan.plan_id}",
                "reason": "The exact release artifact set requires human acceptance.",
            }]
        if state.status == ProjectStatus.COMPLETED_WITH_GAPS:
            gaps = [
                {"item_id": row.item_id, "limitations": row.limitations}
                for row in store.load_work_item_results().values()
                if row.limitations
            ]
            return [{
                "action": "inspect_gaps",
                "reason": state.terminal_reason,
                "work_items": gaps,
            }]
        if state.status in _TERMINAL_PROJECT_STATUSES:
            return [{"action": "inspect_artifacts", "project_id": spec.project_id}]
        return [{"action": "run_project", "project_id": spec.project_id}]

    def _store(self, project_id: str) -> ResearchProjectStore:
        return ResearchProjectStore(self.projects_dir, project_id)

    def _existing_store(self, project_id: str) -> ResearchProjectStore:
        store = self._store(project_id)
        if store.load_spec() is None:
            raise ResearchProjectNotFound(f"project not found: {project_id}")
        return store


__all__ = [
    "ResearchDecisionError",
    "ResearchProjectNotFound",
    "ResearchProjectService",
]
