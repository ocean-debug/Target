"""Append-only evidence/trace store and resumable checkpoints."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, TypeVar

from pydantic import BaseModel

from .contracts import (
    CaseRecord, Claim, EvidenceItem, ExecutionPlan, ReviewerFinding, TargetCard,
    TaskSpec, ToolResult, TraceEvent,
)
from .legacy import migrate_current_contract, parse_task_spec


T = TypeVar("T", bound=BaseModel)


class EvidenceStore:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def _jsonl(self, name: str, item: BaseModel) -> None:
        with (self.run_dir / name).open("a", encoding="utf-8") as handle:
            handle.write(item.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _json(self, name: str, payload: BaseModel | dict[str, Any] | list[Any]) -> Path:
        path = self.run_dir / name
        temp = path.with_suffix(path.suffix + ".tmp")
        if isinstance(payload, BaseModel):
            content = payload.model_dump(mode="json")
        elif isinstance(payload, list):
            content = [v.model_dump(mode="json") if isinstance(v, BaseModel) else v for v in payload]
        else:
            content = payload
        temp.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)
        return path

    def save_task(self, task: TaskSpec) -> None:
        self._json("task_spec.json", task)

    def load_task(self) -> TaskSpec | None:
        path = self.run_dir / "task_spec.json"
        if not path.exists():
            return None
        return parse_task_spec(json.loads(path.read_text(encoding="utf-8")))

    def task_contract_version(self) -> str | None:
        """Return the persisted root version without applying a migration adapter."""
        path = self.run_dir / "task_spec.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        version = payload.get("contract_version")
        return str(version) if version is not None else None

    def has_durable_run_artifacts(self) -> bool:
        names = {
            "checkpoint.json", "execution_plan.json", "tool_results.jsonl",
            "evidence_items.jsonl", "claims.jsonl", "reviewer_findings.jsonl",
            "trace.jsonl", "status.json", "ranked_targets.json", "target_cards.json",
            "case_record.json", "report.json", "report.md",
        }
        return any((self.run_dir / name).exists() for name in names)

    def save_plan(self, plan: ExecutionPlan) -> None:
        self._json("execution_plan.json", plan)

    def add_tool_result(self, result: ToolResult) -> None:
        self._jsonl("tool_results.jsonl", result)

    def add_evidence(self, evidence: EvidenceItem) -> None:
        self._jsonl("evidence_items.jsonl", evidence)

    def add_claim(self, claim: Claim) -> None:
        self._jsonl("claims.jsonl", claim)

    def add_finding(self, finding: ReviewerFinding) -> None:
        self._jsonl("reviewer_findings.jsonl", finding)

    def add_trace(self, event: TraceEvent) -> None:
        self._jsonl("trace.jsonl", event)

    def save_cards(self, cards: list[TargetCard]) -> None:
        self._json("target_cards.json", cards)

    def save_case(self, case: CaseRecord) -> None:
        self._json("case_record.json", case)

    def checkpoint(self, state: dict[str, Any]) -> None:
        self._json("checkpoint.json", state)

    def save_json(self, name: str, payload: BaseModel | dict[str, Any] | list[Any]) -> Path:
        return self._json(name, payload)

    def load_checkpoint(self) -> dict[str, Any] | None:
        path = self.run_dir / "checkpoint.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def read_jsonl(self, name: str, model: type[T]) -> list[T]:
        path = self.run_dir / name
        if not path.exists():
            return []
        return [
            model.model_validate(migrate_current_contract(json.loads(line)))
            for line in path.read_text(encoding="utf-8").splitlines() if line
        ]

    def evidences(self) -> list[EvidenceItem]:
        return self.read_jsonl("evidence_items.jsonl", EvidenceItem)

    def tool_results(self) -> list[ToolResult]:
        return self.read_jsonl("tool_results.jsonl", ToolResult)

    def findings(self) -> list[ReviewerFinding]:
        return self.read_jsonl("reviewer_findings.jsonl", ReviewerFinding)

    def traces(self) -> list[TraceEvent]:
        return self.read_jsonl("trace.jsonl", TraceEvent)

    def assert_referential_integrity(self) -> None:
        results = self.tool_results()
        evidence_items = self.evidences()
        tool_id_list = [item.tool_run_id for item in results]
        evidence_id_list = [item.evidence_id for item in evidence_items]
        if len(tool_id_list) != len(set(tool_id_list)):
            raise ValueError("duplicate ToolResult.tool_run_id values make provenance ambiguous")
        if len(evidence_id_list) != len(set(evidence_id_list)):
            raise ValueError("duplicate EvidenceItem.evidence_id values make provenance ambiguous")
        tool_ids = set(tool_id_list)
        evidence_ids = set(evidence_id_list)
        for evidence in evidence_items:
            if evidence.tool_run_id not in tool_ids:
                raise ValueError(f"evidence {evidence.evidence_id} references missing tool run")
        for result in results:
            missing = set(result.evidence_ids) - evidence_ids
            if missing:
                raise ValueError(f"tool run {result.tool_run_id} references missing evidence: {sorted(missing)}")
        for result in results:
            prior_id = result.supersedes_tool_run_id
            if prior_id is not None:
                if prior_id == result.tool_run_id:
                    raise ValueError(f"tool run {result.tool_run_id} cannot supersede itself")
                if prior_id not in tool_ids:
                    raise ValueError(f"tool run {result.tool_run_id} supersedes a missing tool run: {prior_id}")
        supersession = {
            row.tool_run_id: row.supersedes_tool_run_id
            for row in results
            if row.supersedes_tool_run_id is not None
        }
        for run_id in supersession:
            seen: set[str] = set()
            cursor = run_id
            while cursor in supersession:
                if cursor in seen:
                    raise ValueError("tool result supersession chain contains a cycle")
                seen.add(cursor)
                cursor = supersession[cursor]

    @staticmethod
    def by_gene(items: Iterable[EvidenceItem]) -> dict[str, list[EvidenceItem]]:
        grouped: dict[str, list[EvidenceItem]] = {}
        for item in items:
            if item.gene_symbol:
                grouped.setdefault(item.gene_symbol, []).append(item)
        return grouped
