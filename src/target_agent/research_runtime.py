"""Durable LangGraph runtime for project-level life-science research."""
from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .contracts import utc_now
from .llm import StepClient
from .research_contracts import (
    AssessmentDimension, AssessmentLevel, AssessmentRecord, AssessmentResult, AutonomyMode, DataContract,
    DecisionAction, DecisionEvent, FailureClass, ProjectState, ProjectStatus, RepairAuthorization, ResearchPlan,
    ResearchProjectSpec, TERMINAL_WORK_ITEM_STATUSES, WorkItemResult, WorkItemStatus,
)
from .research_modules import ModuleContext, ResearchModuleRegistry, default_research_registry
from .research_planner import ResearchPlanner
from .research_projection import DomainActivityProjection
from .research_repair import (
    active_assessments,
    active_item_ids,
    build_plan_revision,
    build_repair_resolution,
    canonical_sha256,
    classify_exception,
    effective_plan,
    project_snapshot_digest,
    propose_transient_repair,
    work_item_result_digest,
)
from .research_store import ProjectBusyError, ResearchProjectStore
from .settings import Settings, load_settings


class ResearchRuntimeState(TypedDict, total=False):
    project: ResearchProjectSpec
    project_id: str
    resume: bool
    store: ResearchProjectStore
    plan: ResearchPlan
    results: dict[str, WorkItemResult]
    early_terminal: bool
    execution_done: bool
    execution_paused: bool


class _InputContractError(ValueError):
    pass


def validate_data_contract(
    payload: dict[str, Any], contract: DataContract | None, boundary: str = "output",
) -> list[str]:
    if contract is None:
        return []
    issues = [f"missing required {boundary}: {name}" for name in contract.required_fields if name not in payload]
    expected_types: dict[str, tuple[type, ...]] = {
        "string": (str,), "number": (int, float), "integer": (int,), "boolean": (bool,),
        "object": (dict,), "array": (list,),
    }
    for name, expected in contract.field_types.items():
        if name not in payload:
            continue
        value = payload[name]
        if expected == "integer" and isinstance(value, bool):
            issues.append(f"{boundary} {name} expected integer, got boolean")
        elif expected == "number" and isinstance(value, bool):
            issues.append(f"{boundary} {name} expected number, got boolean")
        elif not isinstance(value, expected_types[expected]):
            issues.append(f"{boundary} {name} expected {expected}, got {type(value).__name__}")
    return issues


def _completed_item_ids(results: dict[str, WorkItemResult]) -> list[str]:
    return sorted(item_id for item_id, result in results.items() if result.status in {
        WorkItemStatus.COMPLETED, WorkItemStatus.COMPLETED_WITH_GAPS,
    })


class ResearchProjectRuntime:
    """Execute a frozen, allowlisted research plan with durable item boundaries."""

    def __init__(
        self,
        projects_dir: Path | None = None,
        cache_dir: Path | None = None,
        registry: ResearchModuleRegistry | None = None,
        planner: ResearchPlanner | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or load_settings()
        self.projects_dir = projects_dir or self.settings.projects_dir
        self.cache_dir = cache_dir or self.settings.cache_dir
        self.registry = registry or default_research_registry(self.settings)
        self.planner = planner or ResearchPlanner(self.registry, StepClient.from_settings(self.settings))
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ResearchRuntimeState)
        graph.add_node("intake", self._intake)
        graph.add_node("plan", self._plan)
        graph.add_node("execute", self._execute_one)
        graph.add_node("repair", self._repair)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "intake")
        graph.add_conditional_edges(
            "intake", lambda state: "terminal" if state["early_terminal"] else "plan",
            {"terminal": END, "plan": "plan"},
        )
        graph.add_conditional_edges(
            "plan", lambda state: "pause" if state.get("execution_paused") else "execute",
            {"pause": END, "execute": "execute"},
        )
        graph.add_conditional_edges(
            "execute", lambda state: (
                "pause" if state.get("execution_paused") else
                "repair" if state["execution_done"] else "execute"
            ),
            {"pause": END, "execute": "execute", "repair": "repair"},
        )
        graph.add_conditional_edges(
            "repair", lambda state: (
                "pause" if state.get("execution_paused") else
                "execute" if not state.get("execution_done", True) else "finalize"
            ),
            {"pause": END, "execute": "execute", "finalize": "finalize"},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    def _intake(self, state: ResearchRuntimeState) -> dict[str, Any]:
        project = state["project"]
        store = ResearchProjectStore(self.projects_dir, project.project_id)
        existing = store.load_spec()
        if existing is not None:
            incoming = project.model_dump(mode="json", exclude={"created_at"})
            stored = existing.model_dump(mode="json", exclude={"created_at"})
            if incoming != stored:
                raise ValueError("project id already exists with a different immutable research goal")
            project = existing
        else:
            store.create(project)
        prior_state = store.load_state()
        store.assert_integrity()
        terminal = prior_state and prior_state.status in {
            ProjectStatus.COMPLETED, ProjectStatus.COMPLETED_WITH_GAPS,
            ProjectStatus.FAILED, ProjectStatus.CANCELLED,
        }
        if terminal and state.get("resume"):
            store.assert_integrity()
            return {"project": project, "store": store, "early_terminal": True,
                    "results": store.load_work_item_results()}
        if terminal:
            raise ValueError("project already reached a terminal state; use resume to inspect it")
        if prior_state is not None and not state.get("resume"):
            raise ValueError("project already has durable progress; use resume to continue it")
        next_state = ProjectState(
            project_id=project.project_id, status=ProjectStatus.RUNNING,
            completed_items=(prior_state.completed_items if prior_state else []),
            failed_items=(prior_state.failed_items if prior_state else []),
            attempts=(prior_state.attempts if prior_state else {}),
        )
        store.save_state(next_state)
        store.append_event("state_transition", "intake", detail={"resume": bool(state.get("resume"))})
        return {"project": project, "store": store, "early_terminal": False,
                "results": store.load_work_item_results() if state.get("resume") else {}}

    def _plan(self, state: ResearchRuntimeState) -> dict[str, Any]:
        store, project = state["store"], state["project"]
        base_plan = store.load_plan()
        new_plan = base_plan is None
        if new_plan:
            base_plan = self.planner.create_plan(project)
            if len(base_plan.items) > project.max_work_items:
                raise ValueError("planner exceeded project max_work_items")
            unknown = sorted({item.module for item in base_plan.items} - set(self.registry.names))
            if unknown:
                raise ValueError(f"plan contains unregistered modules: {unknown}")
            store.save_plan(base_plan)
        assert base_plan is not None
        revisions = store.read_plan_revisions()
        self._validate_repair_overlays(project, store, revisions)
        plan = effective_plan(base_plan, revisions)
        prior_state = store.load_state() or ProjectState(project_id=project.project_id)
        if project.autonomy_mode == AutonomyMode.AUTONOMOUS and not self._accepted(store, base_plan.plan_id):
            store.append_decision(DecisionEvent(
                project_id=project.project_id, action=DecisionAction.ACCEPT, target_ids=[base_plan.plan_id],
                rationale="Plan passed DAG, module allowlist and work-item budget validation.",
                actor="research_runtime", reversible=True,
            ))
        plan_accepted = project.autonomy_mode == AutonomyMode.AUTONOMOUS or self._accepted(store, base_plan.plan_id)
        if not plan_accepted:
            store.save_state(ProjectState(
                project_id=project.project_id, status=ProjectStatus.NEEDS_INPUT,
                completed_items=_completed_item_ids(state["results"]), attempts=prior_state.attempts,
                checkpoint_kind="plan", checkpoint_target_id=base_plan.plan_id,
                terminal_reason=f"Human acceptance is required for plan {base_plan.plan_id}.",
            ))
            store.append_event("human_checkpoint", "plan_approval_required", detail={"plan_id": base_plan.plan_id})
            return {"plan": plan, "execution_paused": True}
        store.save_state(ProjectState(
            project_id=project.project_id, status=ProjectStatus.PLANNED,
            completed_items=_completed_item_ids(state["results"]), attempts=prior_state.attempts,
        ))
        store.append_event("plan_frozen" if new_plan else "plan_resumed", "planned", detail={
            "plan_id": base_plan.plan_id, "planner_backend": plan.planner_backend,
            "work_items": [item.item_id for item in plan.items],
        })
        return {"plan": plan, "execution_paused": False}

    @staticmethod
    def _accepted(store: ResearchProjectStore, target_id: str) -> bool:
        return any(row.action == DecisionAction.ACCEPT and target_id in row.target_ids
                   for row in store.read_decisions())

    @staticmethod
    def _accepted_snapshot(store: ResearchProjectStore, target_id: str, snapshot_digest: str) -> bool:
        return any(
            row.action == DecisionAction.ACCEPT
            and target_id in row.target_ids
            and row.evidence_snapshot_digest == snapshot_digest
            for row in store.read_decisions()
        )

    @staticmethod
    def _has_action(store: ResearchProjectStore, action: DecisionAction) -> bool:
        return any(row.action == action for row in store.read_decisions())

    def _validate_repair_overlays(
        self,
        project: ResearchProjectSpec,
        store: ResearchProjectStore,
        revisions: list,
    ) -> None:
        requests_by_id = {row.repair_request_id: row for row in store.read_repair_requests()}
        for revision in revisions:
            request = requests_by_id[revision.repair_request_id]
            root = next(
                item for item in revision.added_items
                if item.rerun_of_item_id == request.target_work_item_id
            )
            descriptor = self.registry.get(root.module).descriptor
            if not (
                descriptor.side_effect_free
                and descriptor.replay_safe
                and "same_input_retry" in descriptor.repair_modes
            ):
                raise ValueError("persisted repair overlay violates current module repair policy")
            if any(
                not self.registry.get(item.module).descriptor.replay_safe
                or not self.registry.get(item.module).descriptor.side_effect_free
                for item in revision.added_items
            ):
                raise ValueError("persisted repair overlay contains an unsafe downstream module")
            expected_checkpoint = project.autonomy_mode != AutonomyMode.AUTONOMOUS
            if revision.approval_required != expected_checkpoint:
                raise ValueError("persisted repair overlay authorization does not match project autonomy")
            if expected_checkpoint and not self._accepted_snapshot(
                store, request.repair_request_id, request.trigger_snapshot_digest,
            ):
                raise ValueError("persisted repair overlay lacks exact-snapshot approval")

    def _execute_one(self, state: ResearchRuntimeState) -> dict[str, Any]:
        store, project, plan = state["store"], state["project"], state["plan"]
        results = dict(state["results"])
        revisions = store.read_plan_revisions()
        active_ids = active_item_ids(plan, revisions)
        pending = [item for item in plan.items if item.item_id in active_ids and item.item_id not in results]
        if not pending:
            return {"results": results, "execution_done": True, "execution_paused": False}
        item = next((candidate for candidate in pending
                     if all(dependency in results and results[dependency].status in TERMINAL_WORK_ITEM_STATUSES
                            for dependency in candidate.dependencies)), None)
        if item is None:
            raise RuntimeError("no executable work item remains despite an acyclic validated plan")
        prior_state = store.load_state() or ProjectState(project_id=project.project_id)
        attempts = dict(prior_state.attempts)
        if project.autonomy_mode == AutonomyMode.SUPERVISED and not self._accepted(store, item.item_id):
            store.save_state(ProjectState(
                project_id=project.project_id, status=ProjectStatus.NEEDS_INPUT,
                current_item_id=item.item_id, completed_items=_completed_item_ids(results),
                checkpoint_kind="work_item", checkpoint_target_id=item.item_id,
                attempts=attempts, terminal_reason=f"Human acceptance is required for work item {item.item_id}.",
            ))
            store.append_event("human_checkpoint", "work_item_approval_required", work_item_id=item.item_id)
            return {"results": results, "execution_done": False, "execution_paused": True}
        dependency_failures = [dependency for dependency in item.dependencies if results[dependency].status in {
            WorkItemStatus.FAILED, WorkItemStatus.BLOCKED, WorkItemStatus.NEEDS_INPUT,
        }]
        if dependency_failures and item.module not in {"independent_review", "research_report"}:
            result = WorkItemResult(
                item_id=item.item_id, module=item.module, status=WorkItemStatus.BLOCKED,
                summary="The work item was not executed because a required dependency did not complete.",
                limitations=[f"Blocking dependencies: {', '.join(dependency_failures)}"],
            )
            store.save_work_item_result(result)
            results[item.item_id] = result
            store.append_event("work_item_finished", result.status.value, work_item_id=item.item_id,
                               detail={"blocking_dependencies": dependency_failures})
            return {"results": results, "execution_done": active_ids.issubset(results),
                    "execution_paused": False}
        if attempts.get(item.item_id, 0) >= item.max_attempts:
            result = WorkItemResult(
                item_id=item.item_id, module=item.module, status=WorkItemStatus.BLOCKED,
                summary="The work item attempt budget was exhausted after an interrupted or failed attempt.",
                limitations=["A recorded replan or human override is required before another attempt."],
            )
            store.save_work_item_result(result)
            results[item.item_id] = result
            store.append_event("work_item_finished", result.status.value, work_item_id=item.item_id,
                               detail={"attempts": attempts.get(item.item_id, 0), "max_attempts": item.max_attempts})
            return {"results": results, "execution_done": active_ids.issubset(results),
                    "execution_paused": False}
        attempts[item.item_id] = attempts.get(item.item_id, 0) + 1
        store.save_state(ProjectState(
            project_id=project.project_id, status=ProjectStatus.RUNNING, current_item_id=item.item_id,
            completed_items=_completed_item_ids(results), attempts=attempts,
        ))
        store.append_event("work_item_started", "running", work_item_id=item.item_id,
                           detail={"module": item.module, "attempt": attempts[item.item_id]})
        active_results = {item_id: row for item_id, row in results.items() if item_id in active_ids}
        referenced_artifact_ids = {
            artifact_id for result in active_results.values() for artifact_id in result.artifact_ids
        }
        active_artifacts = [
            row for row in store.read_artifacts()
            if row.work_item_id in active_ids and row.artifact_id in referenced_artifact_ids
        ]
        context = ModuleContext(
            project=project, item=item, project_dir=store.project_dir, cache_dir=self.cache_dir,
            settings=self.settings, prior_results=active_results, artifacts=active_artifacts,
            activity_sink=lambda projection: self._record_domain_activity(store, projection),
        )
        try:
            input_payload = {
                **item.inputs,
                "dependencies": {dependency: results[dependency].outputs for dependency in item.dependencies},
            }
            effective_input_digest = canonical_sha256(input_payload)
            supersedes_result_digest: str | None = None
            if item.rerun_of_item_id is not None:
                source_result = results.get(item.rerun_of_item_id)
                if source_result is None:
                    raise ValueError("repair item references a missing source result")
                supersedes_result_digest = work_item_result_digest(source_result)
                request = next(
                    (row for row in store.read_repair_requests()
                     if row.repair_request_id == item.repair_request_id),
                    None,
                )
                if request is None:
                    raise ValueError("repair item references a missing repair request")
                if item.rerun_of_item_id == request.target_work_item_id and effective_input_digest != request.input_digest:
                    raise ValueError("same-input repair changed the effective input digest")
            input_issues = validate_data_contract(input_payload, item.input_contract, boundary="input")
            if input_issues:
                raise _InputContractError("; ".join(input_issues))
            execution = self.registry.get(item.module).execute(context)
            result = execution.result
            if result.item_id != item.item_id or result.module != item.module:
                raise ValueError("module result identity does not match the planned work item")
            registered_ids = list(result.artifact_ids)
            for artifact in execution.artifacts:
                record = store.register_artifact(
                    artifact.path, item.item_id, artifact.logical_name, artifact.media_type,
                )
                registered_ids.append(record.artifact_id)
            issues = validate_data_contract(result.outputs, item.output_contract)
            contract_checkable = result.status in {
                WorkItemStatus.COMPLETED, WorkItemStatus.COMPLETED_WITH_GAPS,
            }
            if issues and contract_checkable:
                result = result.model_copy(update={
                    "status": WorkItemStatus.COMPLETED_WITH_GAPS,
                    "limitations": [*result.limitations, *issues],
                })
                execution.assessments.append(AssessmentRecord(
                    project_id=project.project_id, target_id=item.item_id,
                    dimension=AssessmentDimension.SCHEMA_ALIGNMENT, level=AssessmentLevel.A0,
                    result=AssessmentResult.FAIL, actor="research_runtime",
                    method="deterministic_data_contract_validation", rationale="; ".join(issues), blocking=True,
                ))
            elif issues:
                execution.assessments.append(AssessmentRecord(
                    project_id=project.project_id, target_id=item.item_id,
                    dimension=AssessmentDimension.SCHEMA_ALIGNMENT, level=AssessmentLevel.A0,
                    result=AssessmentResult.NOT_ASSESSED, actor="research_runtime",
                    method="deterministic_data_contract_validation",
                    rationale=("Output contract could not be assessed because the module ended as "
                               f"{result.status.value}: {'; '.join(issues)}"), blocking=False,
                ))
            elif item.output_contract is not None and contract_checkable:
                execution.assessments.append(AssessmentRecord(
                    project_id=project.project_id, target_id=item.item_id,
                    dimension=AssessmentDimension.SCHEMA_ALIGNMENT, level=AssessmentLevel.A0,
                    result=AssessmentResult.PASS, actor="research_runtime",
                    method="deterministic_data_contract_validation",
                    rationale=f"Output satisfies {item.output_contract.schema_id}@{item.output_contract.schema_version}.",
                ))
            result = result.model_copy(update={
                "artifact_ids": list(dict.fromkeys(registered_ids)),
                "input_digest": effective_input_digest,
                "supersedes_result_digest": supersedes_result_digest,
                "repair_request_id": item.repair_request_id,
                "completed_at": utc_now(),
            })
            for assessment in execution.assessments:
                store.append_assessment(assessment)
        except ProjectBusyError:
            raise
        except _InputContractError as exc:
            result = WorkItemResult(
                item_id=item.item_id, module=item.module, status=WorkItemStatus.NEEDS_INPUT,
                summary="The work item input contract is incomplete or misaligned.",
                error=exc.__class__.__name__, failure_class=FailureClass.MISSING_INPUT,
                input_digest=locals().get("effective_input_digest"),
                repair_request_id=item.repair_request_id, limitations=[str(exc)],
            )
            store.append_assessment(AssessmentRecord(
                project_id=project.project_id, target_id=item.item_id,
                dimension=AssessmentDimension.SCHEMA_ALIGNMENT, level=AssessmentLevel.A0,
                result=AssessmentResult.FAIL, actor="research_runtime",
                method="deterministic_input_contract_validation", rationale=str(exc), blocking=True,
            ))
        except Exception as exc:
            result = WorkItemResult(
                item_id=item.item_id, module=item.module, status=WorkItemStatus.FAILED,
                summary="The research module failed without producing an accepted result.",
                error=exc.__class__.__name__, failure_class=classify_exception(exc),
                input_digest=locals().get("effective_input_digest"),
                supersedes_result_digest=locals().get("supersedes_result_digest"),
                repair_request_id=item.repair_request_id,
                limitations=["Inspect the project event ledger before retrying."],
            )
        store.save_work_item_result(result)
        results[item.item_id] = result
        store.append_event("work_item_finished", result.status.value, work_item_id=item.item_id, detail={
            "module": item.module, "artifact_ids": result.artifact_ids,
            "limitations": result.limitations, "error": result.error,
        })
        return {"results": results, "execution_done": active_ids.issubset(results),
                "execution_paused": False}

    @staticmethod
    def _record_domain_activity(
        store: ResearchProjectStore,
        projection: DomainActivityProjection,
    ) -> None:
        """Persist one idempotent project projection of a child TraceEvent."""
        store.append_domain_activity(projection)

    def _repair(self, state: ResearchRuntimeState) -> dict[str, Any]:
        """Apply one deterministic Reviewer-triggered execution overlay."""
        store, project = state["store"], state["project"]
        base_plan = store.load_plan()
        if base_plan is None:
            raise RuntimeError("repair gate requires an immutable base plan")
        revisions = store.read_plan_revisions()
        plan = effective_plan(base_plan, revisions)
        results = dict(state["results"])
        assessments = store.read_assessments()
        artifacts = store.read_artifacts()
        requests = store.read_repair_requests()
        resolutions = store.read_repair_resolutions()
        resolved_request_ids = {row.repair_request_id for row in resolutions}

        for revision in revisions:
            if revision.repair_request_id in resolved_request_ids:
                continue
            request = next(row for row in requests if row.repair_request_id == revision.repair_request_id)
            resolution = build_repair_resolution(
                request=request,
                revision=revision,
                plan=plan,
                results=results,
                assessments=assessments,
                artifacts=artifacts,
                revisions=revisions,
                exhausted=len(revisions) >= project.max_replans,
            )
            if resolution is not None:
                store.append_repair_resolution(resolution)
                store.append_event(
                    "repair_resolved",
                    resolution.status.value,
                    work_item_id=request.target_work_item_id,
                    detail={
                        "repair_request_id": request.repair_request_id,
                        "revision_id": revision.revision_id,
                        "after_snapshot_digest": resolution.after_snapshot_digest,
                    },
                )
                resolutions.append(resolution)
                resolved_request_ids.add(request.repair_request_id)

        request = propose_transient_repair(
            project=project,
            base_plan=base_plan,
            plan=plan,
            results=results,
            assessments=assessments,
            artifacts=artifacts,
            revisions=revisions,
            registry=self.registry,
        )
        if request is None:
            return {"plan": plan, "results": results, "execution_done": True, "execution_paused": False}

        existing_request = next(
            (row for row in requests if row.repair_request_id == request.repair_request_id),
            None,
        )
        if existing_request is None:
            store.append_repair_request(request)
            store.append_event(
                "repair_requested",
                request.authorization.value,
                work_item_id=request.target_work_item_id,
                detail={
                    "repair_request_id": request.repair_request_id,
                    "action": request.action.value,
                    "risk": request.risk.value,
                    "affected_work_item_ids": request.affected_work_item_ids,
                    "trigger_snapshot_digest": request.trigger_snapshot_digest,
                },
            )
        else:
            request = existing_request

        rejected = any(
            row.action == DecisionAction.REJECT and request.repair_request_id in row.target_ids
            for row in store.read_decisions()
        )
        if rejected:
            store.append_event(
                "repair_declined",
                "completed_with_gaps",
                work_item_id=request.target_work_item_id,
                detail={"repair_request_id": request.repair_request_id},
            )
            return {"plan": plan, "results": results, "execution_done": True, "execution_paused": False}

        approved = request.authorization == RepairAuthorization.AUTOMATIC or self._accepted_snapshot(
            store, request.repair_request_id, request.trigger_snapshot_digest,
        )
        if not approved:
            prior_state = store.load_state() or ProjectState(project_id=project.project_id)
            store.save_state(ProjectState(
                project_id=project.project_id,
                status=ProjectStatus.WAITING_REVIEW,
                current_item_id=request.target_work_item_id,
                completed_items=_completed_item_ids(results),
                attempts=prior_state.attempts,
                checkpoint_kind="repair", checkpoint_target_id=request.repair_request_id,
                checkpoint_snapshot_digest=request.trigger_snapshot_digest,
                terminal_reason=f"Repair approval is required for {request.repair_request_id}.",
            ))
            if not any(
                row.event_type == "human_checkpoint"
                and row.detail.get("repair_request_id") == request.repair_request_id
                for row in store.read_events()
            ):
                store.append_event(
                    "human_checkpoint",
                    "repair_approval_required",
                    work_item_id=request.target_work_item_id,
                    detail={
                        "repair_request_id": request.repair_request_id,
                        "trigger_snapshot_digest": request.trigger_snapshot_digest,
                    },
                )
            return {"plan": plan, "results": results, "execution_done": False, "execution_paused": True}

        revision = build_plan_revision(
            request=request,
            base_plan=base_plan,
            plan=plan,
            assessments=assessments,
            artifacts=artifacts,
            revisions=revisions,
        )
        store.append_plan_revision(revision)
        if not any(
            row.action == DecisionAction.REPLAN and revision.revision_id in row.target_ids
            for row in store.read_decisions()
        ):
            store.append_decision(DecisionEvent(
                project_id=project.project_id,
                action=DecisionAction.REPLAN,
                target_ids=[request.repair_request_id, revision.revision_id],
                rationale=request.rationale,
                actor="deterministic_repair_policy",
                evidence_snapshot_digest=request.trigger_snapshot_digest,
                reversible=True,
            ))
        store.append_event(
            "plan_revised",
            "repair_applied",
            work_item_id=request.target_work_item_id,
            detail={
                "repair_request_id": request.repair_request_id,
                "revision_id": revision.revision_id,
                "revision_digest": revision.revision_digest,
                "added_work_item_ids": [row.item_id for row in revision.added_items],
                "superseded_work_item_ids": revision.superseded_item_ids,
            },
        )
        revised_plan = effective_plan(base_plan, [*revisions, revision])
        return {"plan": revised_plan, "results": results, "execution_done": False, "execution_paused": False}

    def _finalize(self, state: ResearchRuntimeState) -> dict[str, Any]:
        store, project, plan, results = state["store"], state["project"], state["plan"], state["results"]
        revisions = store.read_plan_revisions()
        active_ids = active_item_ids(plan, revisions)
        active_results = {item_id: row for item_id, row in results.items() if item_id in active_ids}
        assessments = active_assessments(store.read_assessments(), revisions)
        blocking = [row for row in assessments if row.blocking and row.result == AssessmentResult.FAIL]
        required = [active_results.get(item.item_id) for item in plan.items
                    if item.item_id in active_ids and item.required]
        needs_input = [row for row in required if row is not None and row.status == WorkItemStatus.NEEDS_INPUT]
        hard_failures = [row for row in required if row is None or row.status in {
            WorkItemStatus.FAILED, WorkItemStatus.BLOCKED, WorkItemStatus.SKIPPED,
        }]
        gaps = [row for row in required if row is not None and row.status == WorkItemStatus.COMPLETED_WITH_GAPS]
        active_artifacts = [row for row in store.read_artifacts() if row.work_item_id in active_ids]
        report_artifacts = [row for row in active_artifacts if row.logical_name == "research_report"]
        completed_count = sum(row.status in {WorkItemStatus.COMPLETED, WorkItemStatus.COMPLETED_WITH_GAPS}
                              for row in active_results.values())
        target_items = [item for item in plan.items
                        if item.item_id in active_ids and item.module == "target_discovery"]
        target_result = active_results.get(target_items[-1].item_id) if target_items else None
        if project.domain == "disease_target_discovery" and (
            target_result is None or target_result.outputs.get("deliverables_complete") is not True
        ):
            if target_result is not None and target_result not in needs_input and target_result not in hard_failures:
                gaps.append(target_result)
        if completed_count == 0:
            terminal = ProjectStatus.FAILED
            reason = "No required research work item completed."
        elif needs_input:
            terminal = ProjectStatus.NEEDS_INPUT
            reason = f"Project requires user input for {len(needs_input)} required work item(s)."
        elif hard_failures or gaps or blocking or not report_artifacts:
            terminal = ProjectStatus.COMPLETED_WITH_GAPS
            reason = (f"Project retained {len(hard_failures)} incomplete required items, {len(gaps)} gap-bearing items, "
                      f"{len(blocking)} blocking assessments, and {0 if report_artifacts else 1} missing final reports.")
        else:
            terminal = ProjectStatus.COMPLETED
            reason = "All required work items and release gates completed."
        store.assert_integrity()
        release_snapshot = project_snapshot_digest(
            plan=plan,
            results=results,
            assessments=store.read_assessments(),
            artifacts=store.read_artifacts(),
            revisions=revisions,
        )
        if terminal == ProjectStatus.COMPLETED and project.autonomy_mode != AutonomyMode.AUTONOMOUS:
            release_target = f"release:{release_snapshot}"
            if not self._accepted_snapshot(store, release_target, release_snapshot):
                prior_state = store.load_state() or ProjectState(project_id=project.project_id)
                store.save_state(ProjectState(
                    project_id=project.project_id, status=ProjectStatus.WAITING_REVIEW,
                    completed_items=_completed_item_ids(results), attempts=prior_state.attempts,
                    checkpoint_kind="release", checkpoint_target_id=release_target,
                    checkpoint_snapshot_digest=release_snapshot,
                    terminal_reason=f"Human release acceptance is required for {release_target}.",
                ))
                store.append_event("human_checkpoint", "release_approval_required",
                                   detail={"target_id": release_target})
                return {}
        if terminal in {ProjectStatus.NEEDS_INPUT, ProjectStatus.COMPLETED_WITH_GAPS}:
            action_targets = [row.item_id for row in [*needs_input, *hard_failures] if row is not None]
            action_targets += [row.assessment_id for row in blocking]
            if not any(
                row.action == DecisionAction.REQUEST_EVIDENCE
                and row.evidence_snapshot_digest == release_snapshot
                for row in store.read_decisions()
            ):
                store.append_decision(DecisionEvent(
                    project_id=project.project_id, action=DecisionAction.REQUEST_EVIDENCE,
                    target_ids=list(dict.fromkeys(action_targets)), rationale=reason,
                    actor="research_runtime", evidence_snapshot_digest=release_snapshot, reversible=True,
                ))
        elif terminal == ProjectStatus.COMPLETED:
            if not any(
                row.action == DecisionAction.RELEASE
                and row.evidence_snapshot_digest == release_snapshot
                for row in store.read_decisions()
            ):
                store.append_decision(DecisionEvent(
                    project_id=project.project_id, action=DecisionAction.RELEASE,
                    target_ids=[row.artifact_id for row in report_artifacts], rationale=reason,
                    actor="research_runtime", evidence_snapshot_digest=release_snapshot, reversible=False,
                ))
        failed_ids = [item_id for item_id, row in active_results.items()
                      if row.status in {WorkItemStatus.FAILED, WorkItemStatus.BLOCKED, WorkItemStatus.NEEDS_INPUT}]
        final_state = ProjectState(
            project_id=project.project_id, status=terminal,
            completed_items=_completed_item_ids(active_results), failed_items=sorted(failed_ids),
            attempts=(store.load_state() or ProjectState(project_id=project.project_id)).attempts,
            terminal_reason=reason, updated_at=utc_now(),
        )
        store.save_state(final_state)
        store.append_event("project_terminal", terminal.value, detail={
            "reason": reason,
            "release_snapshot_digest": release_snapshot,
        })
        return {}

    def run(self, project: ResearchProjectSpec, resume: bool = False) -> dict[str, Any]:
        store = ResearchProjectStore(self.projects_dir, project.project_id)
        existing = store.load_spec()
        current = store.load_state()
        if existing is not None:
            incoming_payload = project.model_dump(mode="json", exclude={"created_at"})
            stored_payload = existing.model_dump(mode="json", exclude={"created_at"})
            if incoming_payload != stored_payload:
                raise ValueError("project id already exists with a different immutable research goal")
        if current is not None and not resume:
            raise ValueError("project already has durable progress; use resume to continue or inspect it")
        try:
            with store.execution_lock():
                self._graph.invoke(
                    {"project": project, "project_id": project.project_id, "resume": resume},
                    config={"recursion_limit": project.max_work_items * (project.max_replans + 1) + 20},
                )
        except Exception as exc:
            existing = store.load_spec()
            current = store.load_state()
            terminal = current and current.status in {
                ProjectStatus.COMPLETED, ProjectStatus.COMPLETED_WITH_GAPS,
                ProjectStatus.FAILED, ProjectStatus.CANCELLED,
            }
            if existing is not None and not terminal:
                store.save_state(ProjectState(
                    project_id=project.project_id, status=ProjectStatus.FAILED,
                    completed_items=_completed_item_ids(store.load_work_item_results()),
                    attempts=current.attempts if current else {},
                    terminal_reason=f"Unhandled runtime error: {exc.__class__.__name__}",
                ))
                store.append_event("project_terminal", "failed", detail={"error": exc.__class__.__name__})
            raise
        state = store.load_state()
        if state is None:
            raise RuntimeError("research runtime did not persist project state")
        return state.model_dump(mode="json")


__all__ = ["ResearchProjectRuntime", "ResearchRuntimeState", "validate_data_contract"]
