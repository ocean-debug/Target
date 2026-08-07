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
    ForkDirective,
    ForkMode,
    PlanBranch,
    RepairAction,
    RepairAuthorization,
    RepairDirective,
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
DATASET_SWITCH_POLICY_RULE = "project.domain.same_context_dataset_switch.v1"
CLAIM_DOWNGRADE_POLICY_RULE = "project.domain.claim_downgrade.v1"
EVIDENCE_SUPPLEMENT_POLICY_RULE = "project.domain.evidence_supplement.v1"
EVIDENCE_EXCLUSION_POLICY_RULE = "project.domain.evidence_exclusion.v1"
EVIDENCE_DEPENDENCE_POLICY_RULE = "project.domain.evidence_dependence.v1"

# Typed Reviewer finding categories -> the only deterministic repair they may
# trigger. Anything outside this map is never proposed by the policy layer.
FINDING_TO_ACTION: dict[str, RepairAction] = {
    "causal_overreach": RepairAction.DOWNGRADE_CLAIM,
    "gene_mapping_overreach": RepairAction.DOWNGRADE_CLAIM,
    "evidence_dependence": RepairAction.DOWNGRADE_CLAIM,
    "coverage_gap": RepairAction.SUPPLEMENT_EVIDENCE,
    "missing_provenance": RepairAction.SUPPLEMENT_EVIDENCE,
    "context_mismatch": RepairAction.EXCLUDE_EVIDENCE,
    "conflicting_evidence": RepairAction.EXCLUDE_EVIDENCE,
    "dataset_ineligibility": RepairAction.EXCLUDE_EVIDENCE,
}

# One deterministic downgrade target: derived causal/mechanistic language is
# weakened to INFERRED; the policy never upgrades any claim.
CLAIM_DOWNGRADE_TARGET_CLASS = "INFERRED"

OVERLAY_ACTIONS = frozenset({
    RepairAction.DOWNGRADE_CLAIM,
    RepairAction.SUPPLEMENT_EVIDENCE,
    RepairAction.EXCLUDE_EVIDENCE,
})

# Payload keys the overlay may carry; everything else is rejected so a finding
# can never smuggle a frozen-context or truth change into the overlay.
OVERLAY_ALLOWED_PAYLOAD_KEYS: dict[RepairAction, frozenset[str]] = {
    RepairAction.DOWNGRADE_CLAIM: frozenset({
        "finding_id", "claim_id", "from_class", "to_class", "statement_note",
    }),
    RepairAction.SUPPLEMENT_EVIDENCE: frozenset({"finding_id", "evidence_ids", "lane"}),
    RepairAction.EXCLUDE_EVIDENCE: frozenset({"finding_id", "evidence_refs", "reason"}),
}

DOMAIN_REPAIR_POLICY: dict[RepairAction, tuple[RepairRisk, RepairAuthorization]] = {
    RepairAction.SWITCH_DATASET_SAME_CONTEXT: (
        RepairRisk.R2_SCIENTIFIC_METHOD_CHANGE,
        RepairAuthorization.CHECKPOINT_REQUIRED,
    ),
    RepairAction.SUPPLEMENT_EVIDENCE: (
        RepairRisk.R1_SAME_SCOPE_READ_ONLY,
        RepairAuthorization.AUTOMATIC,
    ),
    RepairAction.EXCLUDE_EVIDENCE: (
        RepairRisk.R2_SCIENTIFIC_METHOD_CHANGE,
        RepairAuthorization.CHECKPOINT_REQUIRED,
    ),
    RepairAction.DOWNGRADE_CLAIM: (
        RepairRisk.R0_DERIVATION_ONLY,
        RepairAuthorization.AUTOMATIC,
    ),
}


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


def _repair_revision_count(revisions: Iterable[ResearchPlanRevision]) -> int:
    """Count only repair overlays; fork branches consume a separate budget."""
    return sum(1 for row in revisions if row.fork_branch_id is None)


def fork_affected_item_ids(
    plan: ResearchPlan,
    target_item_id: str,
    mode: ForkMode,
    active_ids: set[str],
) -> list[str]:
    """Return the work items invalidated by a user fork.

    ``redo`` invalidates the target and every transitive dependant;
    ``restore`` keeps the restored target result and invalidates only its
    dependants.
    """
    if target_item_id not in active_ids:
        raise ValueError(f"fork target is not an active work item: {target_item_id}")
    closure = _descendant_closure(plan, target_item_id, active_ids)
    if mode == ForkMode.RESTORE:
        closure = [item_id for item_id in closure if item_id != target_item_id]
    if not closure:
        raise ValueError("fork target has no invalidatable work items")
    return closure


def build_fork_revision(
    *,
    project: ResearchProjectSpec,
    base_plan: ResearchPlan,
    plan: ResearchPlan,
    revisions: list[ResearchPlanRevision],
    branch: PlanBranch,
    directive: ForkDirective,
    assessments: list[AssessmentRecord],
    artifacts: list[BaseModel],
) -> ResearchPlanRevision:
    """Materialize one fork as an append-only ``fork_rollback`` overlay.

    The overlay replaces every superseded item with a fresh item id bound to
    the branch. Only ``inputs`` may differ from the source item, and only by
    the overrides declared in the immutable ForkDirective.
    """
    number = len(revisions) + 1
    if number > 30:
        raise ValueError("plan revision budget exhausted for fork overlays")
    suffix = f"__fork_{branch.fork_count}"
    by_id = {item.item_id: item for item in plan.items}
    mapping = {item_id: f"{item_id}{suffix}" for item_id in branch.superseded_item_ids}
    added: list[WorkItemSpec] = []
    for item_id in branch.superseded_item_ids:
        source = by_id.get(item_id)
        if source is None:
            raise ValueError(f"fork supersedes unknown work item: {item_id}")
        payload = source.model_dump(mode="json")
        inputs = dict(source.inputs or {})
        override = directive.input_overrides.get(item_id)
        if override:
            inputs.update(override)
        payload.update({
            "item_id": mapping[item_id],
            "dependencies": [mapping.get(dep, dep) for dep in source.dependencies],
            "inputs": inputs,
            "rerun_of_item_id": source.item_id,
            "repair_request_id": None,
            "fork_branch_id": branch.branch_id,
        })
        added.append(WorkItemSpec.model_validate(payload))
    affected_artifact_ids = {
        getattr(row, "artifact_id")
        for row in artifacts
        if getattr(row, "work_item_id", None) in set(branch.superseded_item_ids)
    }
    superseded_assessments = [
        row.assessment_id for row in active_assessments(assessments, revisions)
        if row.target_id in set(branch.superseded_item_ids) | affected_artifact_ids
    ]
    body = {
        "project_id": project.project_id,
        "base_plan_id": base_plan.plan_id,
        "parent_revision_id": revisions[-1].revision_id if revisions else None,
        "revision_number": number,
        "repair_request_id": None,
        "fork_branch_id": branch.branch_id,
        "operation": "fork_rollback",
        "directive_id": None,
        "payload": {
            "mode": directive.mode.value,
            "fork_directive_id": directive.fork_directive_id,
            "rollback_to_attempt_id": directive.rollback_to_attempt_id,
        },
        "added_items": [row.model_dump(mode="json") for row in added],
        "superseded_item_ids": branch.superseded_item_ids,
        "superseded_assessment_ids": superseded_assessments,
        "trigger_snapshot_digest": directive.snapshot_digest,
        "approval_required": (
            directive.mode == ForkMode.RESTORE or project.autonomy_mode != AutonomyMode.AUTONOMOUS
        ),
    }
    digest = canonical_sha256(body)
    return ResearchPlanRevision(
        revision_id=_stable_id("revision", {**body, "revision_digest": digest}),
        revision_digest=digest,
        **body,
    )


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
    if _repair_revision_count(revisions) >= project.max_replans:
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


def _dataset_candidates_from_results(results: dict[str, WorkItemResult]) -> list[dict[str, Any]]:
    """Collect typed dataset candidates from domain module outputs."""
    candidates: list[dict[str, Any]] = []
    for result in results.values():
        for key in ("dataset_candidates", "geo_candidates", "datasets"):
            value = result.outputs.get(key)
            if isinstance(value, list):
                candidates.extend(row for row in value if isinstance(row, dict))
    return candidates


def _domain_findings_from_results(results: dict[str, WorkItemResult]) -> list[dict[str, Any]]:
    """Normalize typed blocking findings emitted by domain modules."""
    findings: list[dict[str, Any]] = []
    for result in results.values():
        rows = result.outputs.get("domain_findings")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            category = str(row.get("category") or "")
            if category not in FINDING_TO_ACTION:
                continue
            if str(row.get("severity") or "major") != "blocking":
                continue
            if str(row.get("finding_status") or "") == "resolved":
                continue
            findings.append({
                "finding_id": str(row.get("finding_id") or row.get("id") or ""),
                "target_work_item_id": result.item_id,
                "category": category,
                "subject": row.get("subject") if isinstance(row.get("subject"), dict) else {},
                "related_ids": [str(value) for value in (row.get("related_ids") or []) if value],
                "message": str(row.get("message") or row.get("required_action") or ""),
            })
    return findings


def _derived_claims(result: WorkItemResult) -> list[dict[str, Any]]:
    rows = result.outputs.get("derived_claims")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("claim_id")]


def _derived_evidence(result: WorkItemResult) -> dict[str, dict[str, Any]]:
    rows = result.outputs.get("evidence_items")
    if not isinstance(rows, list):
        return {}
    return {str(row.get("evidence_id") or ""): row for row in rows if isinstance(row, dict) and row.get("evidence_id")}


def _blocking_domain_review_assessments(
    assessments: list[AssessmentRecord],
    revisions: list[ResearchPlanRevision],
    target_id: str,
    digest: str,
) -> list[AssessmentRecord]:
    return [
        row for row in active_assessments(assessments, revisions)
        if row.target_id == target_id
        and row.target_digest == digest
        and row.blocking
        and row.result == AssessmentResult.FAIL
        and row.method == "typed_domain_review"
    ]


def _overlay_payload_allowed(action: RepairAction, payload: dict[str, Any]) -> bool:
    allowed = OVERLAY_ALLOWED_PAYLOAD_KEYS.get(action)
    if allowed is None:
        return False
    return set(payload) <= allowed


def _propose_domain_finding_repair(
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
    """Propose one typed derived-layer repair from a blocking domain finding.

    R0 (claim downgrade) and R1 (same-scope evidence supplement) are automatic
    after their deterministic gates; R2 (evidence exclusion) always requires a
    checkpoint. Findings outside the typed map are never proposed, so frozen
    scope, truth and thresholds can never be changed by the policy layer.
    """
    if _repair_revision_count(revisions) >= project.max_replans:
        return None
    active_ids = active_item_ids(plan, revisions)
    snapshot_digest = project_snapshot_digest(
        plan=plan, results=results, assessments=assessments, artifacts=artifacts, revisions=revisions,
    )
    for finding in _domain_findings_from_results(results):
        action = FINDING_TO_ACTION[finding["category"]]
        target_id = finding["target_work_item_id"]
        if target_id not in active_ids:
            continue
        item = next((row for row in plan.items if row.item_id == target_id), None)
        if item is None or item.module not in set(getattr(registry, "names", [])):
            continue
        descriptor = registry.get(item.module).descriptor
        if action.value not in getattr(descriptor, "repair_modes", ()):
            continue
        result = results.get(target_id)
        if result is None or result.status not in {
            WorkItemStatus.COMPLETED, WorkItemStatus.COMPLETED_WITH_GAPS,
        }:
            continue
        trigger_digest = work_item_result_digest(result)
        if not _blocking_domain_review_assessments(assessments, revisions, target_id, trigger_digest):
            continue
        related = list(finding["related_ids"])
        if finding["subject"].get("claim_id"):
            related.insert(0, str(finding["subject"]["claim_id"]))
        subject_key = "derived_claims"
        payload: dict[str, Any] = {}
        if action == RepairAction.DOWNGRADE_CLAIM:
            claims = _derived_claims(result)
            claim = next(
                (row for row in claims if str(row.get("claim_id") or "") in related),
                None,
            )
            if claim is None:
                continue
            from_class = str(claim.get("claim_class") or "")
            if from_class == CLAIM_DOWNGRADE_TARGET_CLASS:
                continue  # already at the weakest deterministic class
            payload = {
                "finding_id": finding["finding_id"],
                "claim_id": str(claim["claim_id"]),
                "from_class": from_class,
                "to_class": CLAIM_DOWNGRADE_TARGET_CLASS,
                "statement_note": finding["message"] or "Causal interpretation removed by deterministic policy.",
            }
            rule_id = (
                EVIDENCE_DEPENDENCE_POLICY_RULE
                if finding["category"] == "evidence_dependence"
                else CLAIM_DOWNGRADE_POLICY_RULE
            )
            subject_key = "derived_claims"
        elif action == RepairAction.SUPPLEMENT_EVIDENCE:
            evidence = _derived_evidence(result)
            eligible = [eid for eid in related if eid in evidence and eid not in (result.evidence_refs or [])]
            if not eligible:
                continue
            payload = {
                "finding_id": finding["finding_id"],
                "evidence_ids": eligible,
                "lane": str(finding["subject"].get("lane") or "untyped"),
            }
            rule_id = EVIDENCE_SUPPLEMENT_POLICY_RULE
            subject_key = "evidence_refs"
        elif action == RepairAction.EXCLUDE_EVIDENCE:
            known = set(result.evidence_refs or [])
            excluded = [eid for eid in related if eid in known]
            if not excluded:
                continue
            payload = {
                "finding_id": finding["finding_id"],
                "evidence_refs": excluded,
                "reason": finding["message"] or "Context mismatch or conflicting evidence flagged by the Reviewer.",
            }
            rule_id = EVIDENCE_EXCLUSION_POLICY_RULE
            subject_key = "evidence_refs"
        else:  # pragma: no cover - FINDING_TO_ACTION is closed
            continue
        if not _overlay_payload_allowed(action, payload):
            continue
        risk, authorization = DOMAIN_REPAIR_POLICY[action]
        affected = _descendant_closure(plan, target_id, active_ids)
        directive = RepairDirective(
            directive_id=_stable_id("directive", {
                "project_id": project.project_id,
                "work_item_id": target_id,
                "operation": action.value,
                "payload": payload,
            }),
            project_id=project.project_id,
            work_item_id=target_id,
            operation=action,
            subject_key=subject_key,
            payload=payload,
            expected_risk=risk,
            expected_authorization=authorization,
            rationale=(
                f"Blocking Reviewer finding {finding['finding_id']} ({finding['category']}) "
                f"maps deterministically to {action.value}; the frozen TaskSpec is unchanged."
            ),
        )
        return RepairRequest(
            repair_request_id=_stable_id("repair", {
                "project_id": project.project_id,
                "base_plan_id": base_plan.plan_id,
                "target_work_item_id": target_id,
                "trigger_result_digest": trigger_digest,
                "directive_id": directive.directive_id,
            }),
            project_id=project.project_id,
            base_plan_id=base_plan.plan_id,
            target_work_item_id=target_id,
            trigger_assessment_ids=[
                row.assessment_id
                for row in _blocking_domain_review_assessments(assessments, revisions, target_id, trigger_digest)
            ],
            trigger_result_digest=trigger_digest,
            trigger_snapshot_digest=snapshot_digest,
            failure_class=FailureClass.SCIENTIFIC_GAP,
            action=action,
            risk=risk,
            authorization=authorization,
            affected_work_item_ids=affected,
            input_digest=result.input_digest or canonical_sha256(item.inputs),
            policy_rule_id=rule_id,
            policy_version=REPAIR_POLICY_VERSION,
            directive_id=directive.directive_id,
            directive_payload=directive.payload,
            no_scope_change=True,
            success_criteria=[
                "The derived-layer overlay was applied without modifying source evidence.",
                "The frozen TaskSpec disease, tissue, cell type and stage are unchanged.",
                "The full affected subgraph is recomputed and re-reviewed.",
                "The release snapshot digest is rebound to the new active results.",
            ],
            rationale=directive.rationale,
        )
    return None


def propose_domain_repair(
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
    """Propose one typed, same-context dataset-switch repair.

    Only an eligible work item whose module declares ``alternate_dataset``
    support and whose output contains qualified same-context dataset
    candidates may trigger the repair. The frozen TaskSpec context is never
    changed; only the preferred accession is replaced.
    """
    if _repair_revision_count(revisions) >= project.max_replans:
        return None
    active_ids = active_item_ids(plan, revisions)
    snapshot_digest = project_snapshot_digest(
        plan=plan, results=results, assessments=assessments, artifacts=artifacts, revisions=revisions,
    )
    candidates = _dataset_candidates_from_results(results)
    for item in plan.items:
        if item.item_id not in active_ids or item.module not in set(getattr(registry, "names", [])):
            continue
        descriptor = registry.get(item.module).descriptor
        if "alternate_dataset" not in getattr(descriptor, "repair_modes", ()):
            continue
        result = results.get(item.item_id)
        if result is None or result.status != WorkItemStatus.COMPLETED_WITH_GAPS:
            continue
        rejected = []
        eligible: list[dict[str, Any]] = []
        for row in candidates:
            accession = str(row.get("accession") or row.get("dataset_id") or "")
            status = str(row.get("status") or row.get("qualification") or "")
            if not accession:
                continue
            if status in {"rejected", "ineligible", "unqualified"}:
                rejected.append(accession)
            elif status in {"candidate", "qualified", "eligible", "available"}:
                eligible.append(row)
        if not rejected or not eligible:
            continue
        trigger_digest = work_item_result_digest(result)
        trigger_assessments = [
            row for row in active_assessments(assessments, revisions)
            if row.target_id == item.item_id
            and row.blocking and row.result == AssessmentResult.FAIL
            and row.target_digest == trigger_digest
        ]
        if not trigger_assessments:
            continue
        affected = _descendant_closure(plan, item.item_id, active_ids)
        if any(
            not getattr(registry.get(by_id.module).descriptor, "replay_safe", False)
            or not getattr(registry.get(by_id.module).descriptor, "side_effect_free", False)
            for by_id in plan.items if by_id.item_id in affected
        ):
            continue
        selected = eligible[0]
        payload = {
            "preferred_dataset_accessions": [str(selected.get("accession") or selected.get("dataset_id"))],
            "excluded_dataset_accessions": rejected,
            "replacement_dataset": selected,
        }
        directive = RepairDirective(
            directive_id=_stable_id("directive", {
                "project_id": project.project_id,
                "work_item_id": item.item_id,
                "operation": RepairAction.SWITCH_DATASET_SAME_CONTEXT.value,
                "payload": payload,
            }),
            project_id=project.project_id,
            work_item_id=item.item_id,
            operation=RepairAction.SWITCH_DATASET_SAME_CONTEXT,
            subject_key="dataset_selection",
            payload=payload,
            expected_risk=DOMAIN_REPAIR_POLICY[RepairAction.SWITCH_DATASET_SAME_CONTEXT][0],
            expected_authorization=DOMAIN_REPAIR_POLICY[RepairAction.SWITCH_DATASET_SAME_CONTEXT][1],
            rationale=(
                f"Preferred dataset selection was rejected for {item.item_id}; a same-context "
                f"qualified candidate is available and the frozen TaskSpec remains unchanged."
            ),
        )
        return RepairRequest(
            repair_request_id=_stable_id("repair", {
                "project_id": project.project_id,
                "base_plan_id": base_plan.plan_id,
                "target_work_item_id": item.item_id,
                "trigger_result_digest": trigger_digest,
                "directive_id": directive.directive_id,
            }),
            project_id=project.project_id,
            base_plan_id=base_plan.plan_id,
            target_work_item_id=item.item_id,
            trigger_assessment_ids=[row.assessment_id for row in trigger_assessments],
            trigger_result_digest=trigger_digest,
            trigger_snapshot_digest=snapshot_digest,
            failure_class=FailureClass.SCIENTIFIC_GAP,
            action=RepairAction.SWITCH_DATASET_SAME_CONTEXT,
            risk=DOMAIN_REPAIR_POLICY[RepairAction.SWITCH_DATASET_SAME_CONTEXT][0],
            authorization=DOMAIN_REPAIR_POLICY[RepairAction.SWITCH_DATASET_SAME_CONTEXT][1],
            affected_work_item_ids=affected,
            input_digest=result.input_digest or canonical_sha256(item.inputs),
            policy_rule_id=DATASET_SWITCH_POLICY_RULE,
            policy_version=REPAIR_POLICY_VERSION,
            directive_id=directive.directive_id,
            directive_payload=directive.payload,
            no_scope_change=True,
            success_criteria=[
                "The replacement dataset passed deterministic same-context qualification.",
                "The frozen TaskSpec disease, tissue, cell type and stage are unchanged.",
                "The full affected subgraph is recomputed and re-reviewed.",
                "The release snapshot digest is rebound to the new active results.",
            ],
            rationale=directive.rationale,
        )
    return _propose_domain_finding_repair(
        project=project,
        base_plan=base_plan,
        plan=plan,
        results=results,
        assessments=assessments,
        artifacts=artifacts,
        revisions=revisions,
        registry=registry,
    )


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
        if item_id == request.target_work_item_id and request.directive_id is not None:
            inputs = dict(payload.get("inputs") or {})
            directive_payload = dict(request.directive_payload)
            if request.action in OVERLAY_ACTIONS:
                payload["module"] = "domain_overlay"
                inputs["source_item_id"] = source.item_id
                inputs["domain_overlay"] = {**directive_payload, "operation": request.action.value}
            else:
                override = {
                    "preferred_dataset_accessions": directive_payload.get("preferred_dataset_accessions"),
                    "excluded_dataset_accessions": directive_payload.get("excluded_dataset_accessions"),
                }
                override = {key: value for key, value in override.items() if value is not None}
                inputs["dataset_override"] = override
            payload["inputs"] = inputs
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
        "fork_branch_id": None,
        "operation": request.action.value,
        "directive_id": request.directive_id,
        "payload": getattr(request, "directive_payload", {}),
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


def chain_final_replacement(
    revision: ResearchPlanRevision,
    request: RepairRequest,
    revisions: list[ResearchPlanRevision],
) -> WorkItemSpec:
    """Follow repair replacement chains to the final active work item.

    A repair revision may itself be superseded by a later revision (for example a
    second derived-layer overlay chained on the first). Its final disposition is
    judged against the last replacement still active in the effective plan.
    """
    root = next(
        row for row in revision.added_items
        if row.rerun_of_item_id == request.target_work_item_id
    )
    by_source: dict[str, WorkItemSpec] = {}
    for later in revisions:
        if later.revision_number <= revision.revision_number:
            continue
        by_source.update({row.rerun_of_item_id: row for row in later.added_items})
    final = root
    while final.item_id in by_source:
        final = by_source[final.item_id]
    return final


def build_repair_resolution(
    *,
    request: RepairRequest,
    revision: ResearchPlanRevision,
    project: ResearchProjectSpec,
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
    final_item = chain_final_replacement(revision, request, revisions)
    result = results.get(final_item.item_id)
    if result is None:
        return None
    superseded = final_item.item_id != rerun_item.item_id
    verification = [
        row for row in active_assessments(assessments, revisions)
        if row.target_id == final_item.item_id
        and row.actor in {"independent_review", "fake_independent_review"}
        and row.method == "typed_status_gate"
        and row.target_digest == work_item_result_digest(result)
    ]
    passed_review = any(
        row.result == AssessmentResult.PASS and not row.blocking for row in verification
    )
    overlay_ok = (
        request.action in OVERLAY_ACTIONS
        and final_item.module == "domain_overlay"
        and result.outputs.get("domain_overlay_applied") is True
        and _overlay_payload_allowed(request.action, request.directive_payload)
    )
    same_context = (
        _frozen_context_unchanged(project, rerun_item)
        if request.directive_id is not None and request.action == RepairAction.SWITCH_DATASET_SAME_CONTEXT
        else True
    )
    identical_input = result.input_digest == request.input_digest
    recomputed = [row.item_id for row in revision.added_items]
    if superseded:
        # The whole replacement subgraph was replaced by a later repair revision;
        # the earlier repair succeeds only if the final active plan is complete.
        downstream_completed = all(
            results.get(item_id) is not None
            and results[item_id].status == WorkItemStatus.COMPLETED
            for item_id in active_ids
        )
    else:
        downstream_completed = all(
            results.get(item_id) is not None
            and results[item_id].status == WorkItemStatus.COMPLETED
            for item_id in recomputed
        )
    no_active_blocker = not any(
        row.blocking and row.result == AssessmentResult.FAIL
        for row in active_assessments(assessments, revisions)
    )
    success_gate = (
        result.status == WorkItemStatus.COMPLETED
        and passed_review
        and (same_context or identical_input or overlay_ok)
        and downstream_completed
        and no_active_blocker
    )
    if success_gate:
        status = RepairResolutionStatus.RESOLVED
        rationale = "The repair revision completed and the recomputed subgraph passed independent review."
    elif exhausted:
        status = RepairResolutionStatus.EXHAUSTED
        rationale = "The bounded project repair budget was exhausted without satisfying the success gate."
    else:
        status = RepairResolutionStatus.UNRESOLVED
        rationale = "The repair did not satisfy the typed result, overlay, identical-input and independent-review gates."
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


def project_context_target_task(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return the target task from a work item's inputs or project context."""
    candidate = payload.get("inputs", {}).get("target_task_spec")
    return candidate if isinstance(candidate, dict) else None


def _frozen_context_unchanged(project: ResearchProjectSpec, rerun_item: WorkItemSpec) -> bool:
    """Return True when a domain rerun preserves the frozen biological context."""
    old_task = project.context.get("target_task_spec")
    if not isinstance(old_task, dict):
        return False
    old_context = old_task.get("context") or {}
    override = rerun_item.inputs.get("dataset_override") if isinstance(rerun_item.inputs, dict) else None
    if not isinstance(override, dict):
        return False
    frozen = {"disease", "disease_subtype", "organism", "tissue", "cell_type", "disease_stage", "desired_phenotype"}
    context_keys = {key: value for key, value in old_context.items() if key in frozen}
    allowed_keys = {"preferred_dataset_accessions", "excluded_dataset_accessions"}
    return bool(context_keys) and set(override) <= allowed_keys


__all__ = [
    "CLAIM_DOWNGRADE_POLICY_RULE",
    "DATASET_SWITCH_POLICY_RULE",
    "DOMAIN_REPAIR_POLICY",
    "EVIDENCE_DEPENDENCE_POLICY_RULE",
    "EVIDENCE_EXCLUSION_POLICY_RULE",
    "EVIDENCE_SUPPLEMENT_POLICY_RULE",
    "FINDING_TO_ACTION",
    "OVERLAY_ACTIONS",
    "build_fork_revision",
    "fork_affected_item_ids",
    "REPAIR_POLICY_VERSION",
    "active_assessments",
    "active_item_ids",
    "build_plan_revision",
    "build_repair_resolution",
    "chain_final_replacement",
    "canonical_sha256",
    "classify_exception",
    "effective_plan",
    "project_snapshot_digest",
    "propose_domain_repair",
    "propose_transient_repair",
    "work_item_result_digest",
]
