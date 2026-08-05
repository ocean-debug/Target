"""Deterministic, append-only project repair policy.

The first repair mode is deliberately narrow: an independently reviewed,
typed transient failure may rerun the same-input work item and its transitive
dependants.  This module does not interpret Reviewer prose, switch scientific
methods, add arbitrary modules or change the immutable project question.
"""
from __future__ import annotations

import hashlib
import errno
import json
from typing import Any, Iterable

import requests
from pydantic import BaseModel

from .research_contracts import (
    AssessmentRecord,
    AssessmentResult,
    AutonomyMode,
    FailureClass,
    RepairAction,
    RepairAuthorization,
    RepairRequest,
    RepairResolution,
    RepairResolutionStatus,
    RepairRisk,
    ResearchPlan,
    ResearchPlanRevision,
    ResearchProjectSpec,
    WorkItemResult,
    WorkItemSpec,
    WorkItemStatus,
)


CONTROL_MODULES = frozenset({"project_brief", "independent_review", "research_report"})
REPAIR_POLICY_VERSION = "1.0.0"
SAME_INPUT_POLICY_RULE = "project.transient.same_input_subgraph.v1"


def canonical_sha256(value: BaseModel | dict[str, Any] | list[Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def work_item_result_digest(result: WorkItemResult) -> str:
    return canonical_sha256(result)


def effective_plan(base: ResearchPlan, revisions: Iterable[ResearchPlanRevision]) -> ResearchPlan:
    revisions = list(revisions)
    items = [*base.items]
    for revision in revisions:
        items.extend(revision.added_items)
    payload = base.model_dump(mode="json")
    payload.update({
        "items": [item.model_dump(mode="json") for item in items],
        "planner_backend": f"{base.planner_backend}+repair-overlay:{len(revisions)}",
        "rationale": (
            f"{base.rationale} Applied {len(revisions)} append-only, policy-constrained execution overlay(s)."
        ),
    })
    return ResearchPlan.model_validate(payload)


def active_item_ids(plan: ResearchPlan, revisions: Iterable[ResearchPlanRevision]) -> set[str]:
    superseded = {
        item_id for revision in revisions for item_id in revision.superseded_item_ids
    }
    return {item.item_id for item in plan.items} - superseded


def active_assessments(
    assessments: Iterable[AssessmentRecord],
    revisions: Iterable[ResearchPlanRevision],
) -> list[AssessmentRecord]:
    superseded = {
        assessment_id
        for revision in revisions
        for assessment_id in revision.superseded_assessment_ids
    }
    return [row for row in assessments if row.assessment_id not in superseded]


def project_snapshot_digest(
    *,
    plan: ResearchPlan,
    results: dict[str, WorkItemResult],
    assessments: Iterable[AssessmentRecord],
    artifacts: Iterable[BaseModel],
    revisions: Iterable[ResearchPlanRevision],
) -> str:
    revisions = list(revisions)
    active_ids = active_item_ids(plan, revisions)
    active_results = {
        item_id: result.model_dump(mode="json")
        for item_id, result in sorted(results.items())
        if item_id in active_ids
    }
    active_artifact_ids = {
        artifact_id
        for result in results.values()
        if result.item_id in active_ids
        for artifact_id in result.artifact_ids
    }
    active_artifacts = [
        row.model_dump(mode="json")
        for row in artifacts
        if getattr(row, "work_item_id", None) in active_ids
        and getattr(row, "artifact_id", None) in active_artifact_ids
    ]
    active_targets = active_ids | active_artifact_ids
    payload = {
        "base_plan_id": plan.plan_id,
        "revision_digests": [row.revision_digest for row in revisions],
        "active_results": active_results,
        "active_assessments": [
            row.model_dump(mode="json")
            for row in active_assessments(assessments, revisions)
            if row.target_id in active_targets
        ],
        "active_artifacts": active_artifacts,
    }
    return canonical_sha256(payload)


def classify_exception(exc: BaseException) -> FailureClass:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError, ConnectionError, TimeoutError)):
        return FailureClass.TRANSIENT
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        return FailureClass.TRANSIENT if status == 429 or (status is not None and status >= 500) \
            else FailureClass.PERMANENT
    if isinstance(exc, OSError):
        transient_errno = {
            errno.EAGAIN, errno.ECONNREFUSED, errno.ECONNRESET, errno.EHOSTUNREACH,
            errno.ENETDOWN, errno.ENETUNREACH, errno.ETIMEDOUT,
        }
        return FailureClass.TRANSIENT if exc.errno in transient_errno else FailureClass.PERMANENT
    return FailureClass.INTERNAL


def _descendant_closure(plan: ResearchPlan, root_id: str, active_ids: set[str]) -> list[str]:
    affected = {root_id}
    changed = True
    while changed:
        changed = False
        for item in plan.items:
            if item.item_id not in active_ids or item.item_id in affected:
                continue
            if set(item.dependencies) & affected:
                affected.add(item.item_id)
                changed = True
    return [item.item_id for item in plan.items if item.item_id in affected]


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}-{canonical_sha256(payload)[:24]}"


def propose_transient_repair(
    *,
    project: ResearchProjectSpec,
    base_plan: ResearchPlan,
    plan: ResearchPlan,
    results: dict[str, WorkItemResult],
    assessments: list[AssessmentRecord],
    artifacts: list[BaseModel],
    revisions: list[ResearchPlanRevision],
    registry: Any,
) -> RepairRequest | None:
    """Return one source-bound repair request or ``None``.

    Only typed transient failures with an exact input digest, a blocking
    independent assessment and replay-safe module descriptors are eligible.
    """
    if len(revisions) >= project.max_replans:
        return None
    active_ids = active_item_ids(plan, revisions)
    snapshot_digest = project_snapshot_digest(
        plan=plan,
        results=results,
        assessments=assessments,
        artifacts=artifacts,
        revisions=revisions,
    )
    for item in plan.items:
        if item.item_id not in active_ids or item.module in CONTROL_MODULES:
            continue
        result = results.get(item.item_id)
        if (
            result is None
            or result.status != WorkItemStatus.FAILED
            or result.failure_class != FailureClass.TRANSIENT
            or result.input_digest is None
        ):
            continue
        trigger_digest = work_item_result_digest(result)
        trigger_assessments = [
            row for row in active_assessments(assessments, revisions)
            if row.target_id == item.item_id
            and row.blocking
            and row.result == AssessmentResult.FAIL
            and row.target_digest == trigger_digest
        ]
        if not trigger_assessments:
            continue
        descriptor = registry.get(item.module).descriptor
        if not (
            getattr(descriptor, "side_effect_free", False)
            and getattr(descriptor, "replay_safe", False)
            and "same_input_retry" in getattr(descriptor, "repair_modes", ())
        ):
            continue
        affected = _descendant_closure(plan, item.item_id, active_ids)
        if any(
            not getattr(registry.get(by_id.module).descriptor, "replay_safe", False)
            or not getattr(registry.get(by_id.module).descriptor, "side_effect_free", False)
            for by_id in plan.items if by_id.item_id in affected
        ):
            continue
        authorization = (
            RepairAuthorization.AUTOMATIC
            if project.autonomy_mode == AutonomyMode.AUTONOMOUS
            else RepairAuthorization.CHECKPOINT_REQUIRED
        )
        identity = {
            "project_id": project.project_id,
            "base_plan_id": base_plan.plan_id,
            "target_work_item_id": item.item_id,
            "trigger_result_digest": trigger_digest,
            "trigger_snapshot_digest": snapshot_digest,
            "action": RepairAction.RERUN_SUBGRAPH_SAME_INPUTS.value,
            "policy_rule_id": SAME_INPUT_POLICY_RULE,
        }
        return RepairRequest(
            repair_request_id=_stable_id("repair", identity),
            project_id=project.project_id,
            base_plan_id=base_plan.plan_id,
            target_work_item_id=item.item_id,
            trigger_assessment_ids=[row.assessment_id for row in trigger_assessments],
            trigger_result_digest=trigger_digest,
            trigger_snapshot_digest=snapshot_digest,
            failure_class=FailureClass.TRANSIENT,
            action=RepairAction.RERUN_SUBGRAPH_SAME_INPUTS,
            risk=RepairRisk.R1_SAME_SCOPE_READ_ONLY,
            authorization=authorization,
            affected_work_item_ids=affected,
            input_digest=result.input_digest,
            policy_rule_id=SAME_INPUT_POLICY_RULE,
            policy_version=REPAIR_POLICY_VERSION,
            success_criteria=[
                "The retried root work item completes with the identical effective input digest.",
                "Every affected downstream work item is recomputed from the new active result.",
                "Independent review is rerun and the release snapshot is rebound.",
            ],
            rationale=(
                "A replay-safe, side-effect-free module ended with a typed transient failure. "
                "Policy permits one bounded same-input subgraph rerun."
            ),
        )
    return None


def build_plan_revision(
    *,
    request: RepairRequest,
    base_plan: ResearchPlan,
    plan: ResearchPlan,
    assessments: list[AssessmentRecord],
    artifacts: list[BaseModel],
    revisions: list[ResearchPlanRevision],
) -> ResearchPlanRevision:
    number = len(revisions) + 1
    suffix = f"__repair_{number}"
    by_id = {item.item_id: item for item in plan.items}
    mapping = {item_id: f"{item_id}{suffix}" for item_id in request.affected_work_item_ids}
    added: list[WorkItemSpec] = []
    for item_id in request.affected_work_item_ids:
        source = by_id[item_id]
        payload = source.model_dump(mode="json")
        payload.update({
            "item_id": mapping[item_id],
            "dependencies": [mapping.get(dep, dep) for dep in source.dependencies],
            "rerun_of_item_id": source.item_id,
            "repair_request_id": request.repair_request_id,
        })
        added.append(WorkItemSpec.model_validate(payload))
    affected_artifact_ids = {
        getattr(row, "artifact_id")
        for row in artifacts
        if getattr(row, "work_item_id", None) in request.affected_work_item_ids
    }
    superseded_assessments = [
        row.assessment_id for row in active_assessments(assessments, revisions)
        if row.target_id in set(request.affected_work_item_ids) | affected_artifact_ids
    ]
    body = {
        "project_id": request.project_id,
        "base_plan_id": base_plan.plan_id,
        "parent_revision_id": revisions[-1].revision_id if revisions else None,
        "revision_number": number,
        "repair_request_id": request.repair_request_id,
        "operation": "rerun_subgraph_same_inputs",
        "added_items": [row.model_dump(mode="json") for row in added],
        "superseded_item_ids": request.affected_work_item_ids,
        "superseded_assessment_ids": superseded_assessments,
        "trigger_snapshot_digest": request.trigger_snapshot_digest,
        "approval_required": request.authorization == RepairAuthorization.CHECKPOINT_REQUIRED,
    }
    digest = canonical_sha256(body)
    return ResearchPlanRevision(
        revision_id=_stable_id("revision", {**body, "revision_digest": digest}),
        revision_digest=digest,
        **body,
    )


def build_repair_resolution(
    *,
    request: RepairRequest,
    revision: ResearchPlanRevision,
    plan: ResearchPlan,
    results: dict[str, WorkItemResult],
    assessments: list[AssessmentRecord],
    artifacts: list[BaseModel],
    revisions: list[ResearchPlanRevision],
    exhausted: bool,
) -> RepairResolution | None:
    rerun_item = next(
        (row for row in revision.added_items if row.rerun_of_item_id == request.target_work_item_id),
        None,
    )
    if rerun_item is None or rerun_item.item_id not in results:
        return None
    active_ids = active_item_ids(plan, revisions)
    if any(item_id not in results for item_id in active_ids):
        return None
    result = results[rerun_item.item_id]
    verification = [
        row for row in active_assessments(assessments, revisions)
        if row.target_id == rerun_item.item_id
        and row.actor in {"independent_review", "fake_independent_review"}
        and row.method == "typed_status_gate"
        and row.target_digest == work_item_result_digest(result)
    ]
    passed_review = any(
        row.result == AssessmentResult.PASS and not row.blocking for row in verification
    )
    identical_input = result.input_digest == request.input_digest
    recomputed = [row.item_id for row in revision.added_items]
    downstream_completed = all(
        results.get(item_id) is not None
        and results[item_id].status == WorkItemStatus.COMPLETED
        for item_id in recomputed
    )
    no_active_blocker = not any(
        row.blocking and row.result == AssessmentResult.FAIL
        for row in active_assessments(assessments, revisions)
    )
    if (result.status == WorkItemStatus.COMPLETED and passed_review and identical_input
            and downstream_completed and no_active_blocker):
        status = RepairResolutionStatus.RESOLVED
        rationale = "The same-input retry completed and the recomputed subgraph passed independent review."
    elif exhausted:
        status = RepairResolutionStatus.EXHAUSTED
        rationale = "The bounded project repair budget was exhausted without satisfying the success gate."
    else:
        status = RepairResolutionStatus.UNRESOLVED
        rationale = "The retry did not satisfy the typed result, identical-input and independent-review gates."
    after = project_snapshot_digest(
        plan=plan,
        results=results,
        assessments=assessments,
        artifacts=artifacts,
        revisions=revisions,
    )
    identity = {
        "repair_request_id": request.repair_request_id,
        "revision_id": revision.revision_id,
        "after_snapshot_digest": after,
        "status": status.value,
    }
    return RepairResolution(
        resolution_id=_stable_id("resolution", identity),
        project_id=request.project_id,
        repair_request_id=request.repair_request_id,
        revision_id=revision.revision_id,
        status=status,
        before_snapshot_digest=request.trigger_snapshot_digest,
        after_snapshot_digest=after,
        verification_assessment_ids=[row.assessment_id for row in verification],
        active_work_item_ids=sorted(active_ids),
        rationale=rationale,
    )


__all__ = [
    "REPAIR_POLICY_VERSION",
    "active_assessments",
    "active_item_ids",
    "build_plan_revision",
    "build_repair_resolution",
    "canonical_sha256",
    "classify_exception",
    "effective_plan",
    "project_snapshot_digest",
    "propose_transient_repair",
    "work_item_result_digest",
]
