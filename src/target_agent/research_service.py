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
    DomainActivityPage,
    ProjectStatus,
    RepairQueueSnapshot,
    ResearchGoal,
    ResearchProjectSnapshot,
    ResearchProjectSpec,
)
from .research_runtime import ResearchProjectRuntime
from .research_projection import summarize_domain_activities
from .research_repair import active_item_ids, effective_plan, project_snapshot_digest
from .research_store import ProjectBusyError, ResearchProjectStore


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
        project, base_plan = store.load_spec(), store.load_plan()
        if project is None or base_plan is None:
            raise ResearchDecisionError("project does not yet have a frozen plan")
        revisions = store.read_plan_revisions()
        plan = effective_plan(base_plan, revisions)
        release_snapshot = self._release_snapshot(store, plan)
        release_target = f"release:{release_snapshot}"
        allowed = {
            base_plan.plan_id,
            *(item.item_id for item in plan.items),
            release_target,
        }
        if target_id not in allowed:
            raise ResearchDecisionError("decision target is not part of the frozen project plan")
        decision_digest = release_snapshot if target_id == release_target else None
        decision = next(
            (
                row
                for row in store.read_decisions()
                if row.action == DecisionAction.ACCEPT
                and target_id in row.target_ids
                and row.evidence_snapshot_digest == decision_digest
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
                evidence_snapshot_digest=decision_digest,
                reversible=False,
            )
            store.append_decision(decision)
        if resume:
            self.runtime.run(project, resume=True)
        return {
            "decision": decision.model_dump(mode="json"),
            "project": self.snapshot(project_id),
        }

    def decide_repair(
        self,
        *,
        project_id: str,
        repair_request_id: str,
        trigger_snapshot_digest: str,
        approve: bool,
        actor: str,
        rationale: str,
        resume: bool = False,
    ) -> dict[str, Any]:
        """Approve or reject one exact, immutable repair request snapshot."""
        if not actor.strip() or not rationale.strip():
            raise ResearchDecisionError("actor and rationale are required")
        store = self._existing_store(project_id)
        request = next(
            (row for row in store.read_repair_requests() if row.repair_request_id == repair_request_id),
            None,
        )
        if request is None:
            raise ResearchDecisionError("repair request does not exist")
        if request.trigger_snapshot_digest != trigger_snapshot_digest:
            raise ResearchDecisionError("stale repair snapshot digest")
        action = DecisionAction.ACCEPT if approve else DecisionAction.REJECT
        opposite = DecisionAction.REJECT if approve else DecisionAction.ACCEPT
        try:
            with store.execution_lock():
                decisions = store.read_decisions()
                if any(
                    row.action == opposite
                    and repair_request_id in row.target_ids
                    and row.evidence_snapshot_digest == trigger_snapshot_digest
                    for row in decisions
                ):
                    raise ResearchDecisionError("repair request already has an immutable opposite decision")
                decision = next(
                    (
                        row for row in decisions
                        if row.action == action
                        and repair_request_id in row.target_ids
                        and row.evidence_snapshot_digest == trigger_snapshot_digest
                    ),
                    None,
                )
                if decision is None:
                    decision = DecisionEvent(
                        project_id=project_id,
                        action=action,
                        target_ids=[repair_request_id],
                        actor=actor.strip(),
                        rationale=rationale.strip(),
                        evidence_snapshot_digest=trigger_snapshot_digest,
                        reversible=False,
                    )
                    store.append_decision(decision)
        except ProjectBusyError as exc:
            raise ResearchDecisionError("project decision is busy; retry") from exc
        project = store.load_spec()
        if resume and project is not None:
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
        base_plan = store.load_plan()
        revisions = store.read_plan_revisions()
        plan = effective_plan(base_plan, revisions) if base_plan is not None else None
        results = store.load_work_item_results()
        events = store.read_events()
        activities = store.read_domain_activities()
        return ResearchProjectSnapshot(
            spec=spec,
            state=state,
            plan=plan,
            work_item_results=[results[key] for key in sorted(results)],
            artifacts=store.read_artifacts(),
            assessments=store.read_assessments(),
            decisions=store.read_decisions(),
            event_cursor=events[-1].sequence if events else 0,
            domain_activity_cursor=activities[-1].sequence if activities else 0,
            domain_stage_summary=summarize_domain_activities(activities),
            repair_requests=store.read_repair_requests(),
            plan_revisions=revisions,
            repair_resolutions=store.read_repair_resolutions(),
            active_work_item_ids=sorted(active_item_ids(plan, revisions)) if plan is not None else [],
            release_snapshot_digest=self._release_snapshot(store, plan) if plan is not None else None,
            next_actions=self._next_actions(store),
        ).model_dump(mode="json")

    def repairs(self, project_id: str) -> dict[str, Any]:
        store = self._existing_store(project_id)
        spec = store.load_spec()
        assert spec is not None
        revisions = store.read_plan_revisions()
        return RepairQueueSnapshot(
            project_id=project_id,
            requests=store.read_repair_requests(),
            revisions=revisions,
            resolutions=store.read_repair_resolutions(),
            remaining_replans=max(0, spec.max_replans - len(revisions)),
        ).model_dump(mode="json")

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

    def domain_activities(
        self,
        project_id: str,
        *,
        after_sequence: int = 0,
        limit: int = 200,
        work_item_id: str | None = None,
    ) -> dict[str, Any]:
        """Page through the safe, source-linked child workflow activity index."""
        if after_sequence < 0:
            raise ValueError("after_sequence must be non-negative")
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        store = self._existing_store(project_id)
        available = store.read_domain_activities(
            after_sequence=after_sequence,
            work_item_id=work_item_id,
        )
        page = available[:limit]
        return DomainActivityPage(
            project_id=project_id,
            activities=page,
            next_cursor=page[-1].sequence if page else after_sequence,
            has_more=len(available) > len(page),
        ).model_dump(mode="json")

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
                "get_domain_activities",
                "get_repairs",
                "decide_repair",
                "accept_checkpoint",
                "read_text_artifact",
            ],
            "autonomy_modes": [mode.value for mode in AutonomyMode],
            "module_capabilities": self.runtime.registry.public_capabilities(),
            "boundaries": [
                "No arbitrary model-generated code or shell execution is exposed by this service.",
                "Missing biological context remains missing and may require user input.",
                "MCP/HTTP clients receive durable projections, not filesystem deployment paths.",
                "Automatic repair is limited to source-bound same-input reruns of replay-safe transient failures.",
            ],
        }

    def _next_actions(self, store: ResearchProjectStore) -> list[dict[str, Any]]:
        spec, state, plan = store.load_spec(), store.load_state(), store.load_plan()
        if spec is None:
            return []
        if state is None:
            return [{"action": "run_project", "project_id": spec.project_id}]
        if state.checkpoint_kind == "plan":
            return [{
                "action": "accept_checkpoint", "target_id": state.checkpoint_target_id,
                "reason": "The frozen plan requires human acceptance.",
            }]
        if state.checkpoint_kind == "work_item":
            return [{
                "action": "accept_checkpoint", "target_id": state.checkpoint_target_id,
                "reason": "The supervised work item requires human acceptance or additional input.",
            }]
        if state.checkpoint_kind == "repair":
            request = next(
                row for row in store.read_repair_requests()
                if row.repair_request_id == state.checkpoint_target_id
            )
            decided = any(
                request.repair_request_id in decision.target_ids
                and decision.action in {DecisionAction.ACCEPT, DecisionAction.REJECT}
                for decision in store.read_decisions()
            )
            if decided:
                return [{
                    "action": "run_project", "project_id": spec.project_id,
                    "reason": "A durable repair decision must be reconciled before release review.",
                }]
            return [{
                "action": "decide_repair",
                "repair_request_id": request.repair_request_id,
                "trigger_snapshot_digest": request.trigger_snapshot_digest,
                "risk": request.risk.value,
                "affected_work_item_ids": request.affected_work_item_ids,
                "reason": request.rationale,
            }]
        if state.checkpoint_kind == "release":
            return [{
                "action": "accept_checkpoint",
                "target_id": state.checkpoint_target_id,
                "evidence_snapshot_digest": state.checkpoint_snapshot_digest,
                "reason": "The exact release artifact set requires human acceptance.",
            }]
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
        pending_repairs = [
            row for row in store.read_repair_requests()
            if not any(row.repair_request_id == revision.repair_request_id
                       for revision in store.read_plan_revisions())
            and not any(row.repair_request_id in decision.target_ids
                        and decision.action in {DecisionAction.ACCEPT, DecisionAction.REJECT}
                        for decision in store.read_decisions())
        ]
        if state.status == ProjectStatus.WAITING_REVIEW and pending_repairs:
            request = pending_repairs[0]
            return [{
                "action": "decide_repair",
                "repair_request_id": request.repair_request_id,
                "trigger_snapshot_digest": request.trigger_snapshot_digest,
                "risk": request.risk.value,
                "affected_work_item_ids": request.affected_work_item_ids,
                "reason": request.rationale,
            }]
        decided_unapplied_repairs = [
            request for request in store.read_repair_requests()
            if not any(request.repair_request_id == revision.repair_request_id
                       for revision in store.read_plan_revisions())
            and any(request.repair_request_id in decision.target_ids
                    and decision.action in {DecisionAction.ACCEPT, DecisionAction.REJECT}
                    for decision in store.read_decisions())
        ]
        if state.status == ProjectStatus.WAITING_REVIEW and decided_unapplied_repairs:
            return [{
                "action": "run_project",
                "project_id": spec.project_id,
                "reason": "A durable repair decision must be reconciled before release review.",
            }]
        if state.status == ProjectStatus.WAITING_REVIEW and plan is not None:
            effective = effective_plan(plan, store.read_plan_revisions())
            release_snapshot = self._release_snapshot(store, effective)
            return [{
                "action": "accept_checkpoint",
                "target_id": f"release:{release_snapshot}",
                "evidence_snapshot_digest": release_snapshot,
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

    @staticmethod
    def _release_snapshot(store: ResearchProjectStore, plan) -> str:
        return project_snapshot_digest(
            plan=plan,
            results=store.load_work_item_results(),
            assessments=store.read_assessments(),
            artifacts=store.read_artifacts(),
            revisions=store.read_plan_revisions(),
        )

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
