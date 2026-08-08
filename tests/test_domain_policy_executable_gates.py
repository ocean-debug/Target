"""Executable closure gates for the domain repair policy (P0.4).

The deterministic repair policy must stay a closed set: every typed finding
category either maps to one deterministic action or is explicitly refused,
every overlay payload key is whitelisted, every action carries executable
success criteria, and superseded tool results stay in the append-only ledger.
These tests assert the gates themselves so a new repair mode cannot silently
bypass store integrity or provenance accounting.
"""
from __future__ import annotations

import pytest

from target_agent import research_repair as rr
from target_agent.contracts import (
    CoverageStatus, ToolCapability, ToolResult, ToolStatus,
)
from target_agent.research_contracts import (
    FailureClass, RepairAction, RepairAuthorization, RepairRequest, RepairRisk,
)
from target_agent.store import EvidenceStore


def _repair_request(
    action: RepairAction, *, flag: bool = False, **overrides,
) -> RepairRequest:
    values = dict(
        repair_request_id="repair-" + "a" * 24,
        project_id="project-policy-gate",
        base_plan_id="plan-test",
        target_work_item_id="target_discovery",
        trigger_assessment_ids=["assessment-" + "b" * 24],
        trigger_result_digest="0" * 64,
        trigger_snapshot_digest="1" * 64,
        failure_class=FailureClass.SCIENTIFIC_GAP,
        action=action,
        risk=RepairRisk.R1_SAME_SCOPE_READ_ONLY,
        authorization=RepairAuthorization.AUTOMATIC,
        affected_work_item_ids=["target_discovery"],
        input_digest="2" * 64,
        policy_rule_id="test-rule",
        success_criteria=["typed success gate"],
        rationale="Executable policy gate test fixture.",
    )
    values.update(overrides)
    if flag:
        values["candidate_lane_recompute_required"] = True
    return RepairRequest(**values)


def _tool_result(run_id: str, *, supersedes: str | None = None) -> ToolResult:
    return ToolResult(
        tool_run_id=run_id,
        tool_name="europe_pmc_rag",
        tool_version="test",
        status=ToolStatus.SUCCESS,
        coverage_status=CoverageStatus.COVERED,
        context_match_score=1.0,
        outputs={"ok": True},
        capability=ToolCapability(validation_scope="test"),
        supersedes_tool_run_id=supersedes,
    )


def test_verify_domain_repair_policy_passes_on_current_constants():
    rr.verify_domain_repair_policy()


def test_verify_domain_repair_policy_detects_finding_action_drift(monkeypatch):
    drifted = dict(rr.FINDING_TO_ACTION)
    drifted["new_finding_category"] = RepairAction.DOWNGRADE_CLAIM
    monkeypatch.setattr(rr, "FINDING_TO_ACTION", drifted)
    with pytest.raises(ValueError, match="drifted"):
        rr.verify_domain_repair_policy()


def test_verify_domain_repair_policy_detects_overlay_payload_drift(monkeypatch):
    drifted = dict(rr.OVERLAY_ALLOWED_PAYLOAD_KEYS)
    drifted[RepairAction.SWITCH_DATASET_SAME_CONTEXT] = frozenset({"unexpected_key"})
    monkeypatch.setattr(rr, "OVERLAY_ALLOWED_PAYLOAD_KEYS", drifted)
    with pytest.raises(ValueError, match="drifted"):
        rr.verify_domain_repair_policy()


def test_verify_domain_repair_policy_detects_action_policy_drift(monkeypatch):
    drifted = dict(rr.DOMAIN_REPAIR_POLICY)
    drifted.pop(RepairAction.SUPPLEMENT_EVIDENCE)
    monkeypatch.setattr(rr, "DOMAIN_REPAIR_POLICY", drifted)
    with pytest.raises(ValueError, match="references an action missing"):
        rr.verify_domain_repair_policy()


def test_repair_request_binds_candidate_lane_recompute_to_switch_action():
    _repair_request(RepairAction.SWITCH_DATASET_SAME_CONTEXT, flag=True)
    _repair_request(RepairAction.DOWNGRADE_CLAIM)
    with pytest.raises(ValueError, match="candidate_lane_recompute_required"):
        _repair_request(RepairAction.SWITCH_DATASET_SAME_CONTEXT)
    with pytest.raises(ValueError, match="candidate_lane_recompute_required"):
        _repair_request(RepairAction.DOWNGRADE_CLAIM, flag=True)


def test_supersession_chain_rejects_orphan_reference(tmp_path):
    store = EvidenceStore(tmp_path / "run")
    store.add_tool_result(_tool_result("tool-" + "a" * 12, supersedes="tool-" + "b" * 12))
    with pytest.raises(ValueError, match="supersedes a missing tool run"):
        store.assert_referential_integrity()


def test_supersession_chain_rejects_cycle(tmp_path):
    store = EvidenceStore(tmp_path / "run")
    store.add_tool_result(_tool_result("tool-" + "a" * 12, supersedes="tool-" + "b" * 12))
    store.add_tool_result(_tool_result("tool-" + "b" * 12, supersedes="tool-" + "a" * 12))
    with pytest.raises(ValueError, match="cycle"):
        store.assert_referential_integrity()


def test_supersession_chain_keeps_superseded_result_in_ledger(tmp_path):
    store = EvidenceStore(tmp_path / "run")
    store.add_tool_result(_tool_result("tool-" + "a" * 12))
    store.add_tool_result(_tool_result("tool-" + "b" * 12, supersedes="tool-" + "a" * 12))
    store.assert_referential_integrity()
    assert [row.tool_run_id for row in store.tool_results()] == [
        "tool-" + "a" * 12, "tool-" + "b" * 12,
    ]
