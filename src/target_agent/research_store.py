"""Durable project store for the generic scientific research runtime.

The project directory is the unit of recovery. Mutable snapshots use atomic
replacement, while audit records are append-only JSON Lines files. Artifacts
are copied into a content-addressed area so later edits to a work file cannot
silently change the evidence that a decision reviewed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .research_contracts import (
    ArtifactRecord,
    AssessmentRecord,
    DecisionEvent,
    ProjectEvent,
    ProjectState,
    ResearchPlan,
    ResearchProjectSpec,
    WorkItemResult,
)


T = TypeVar("T", bound=BaseModel)
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ProjectBusyError(RuntimeError):
    pass


class ResearchProjectStore:
    """Filesystem-backed store for one research project."""

    def __init__(self, projects_dir: Path | str, project_id: str):
        self.project_id = self._safe_component(project_id, "project_id")
        self.projects_dir = Path(projects_dir).expanduser().resolve()
        self.project_dir = (self.projects_dir / self.project_id).resolve()
        if not self.project_dir.is_relative_to(self.projects_dir):
            raise ValueError("project directory escapes projects root")
        self._lock = threading.RLock()

    @staticmethod
    def _safe_component(value: str, label: str) -> str:
        if not _SAFE_COMPONENT.fullmatch(value):
            raise ValueError(f"unsafe {label}: {value!r}")
        return value

    @staticmethod
    def _payload(value: BaseModel | dict[str, Any] | list[Any]) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value]
        return value

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        """Persist a rename where the platform permits directory fsync."""
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _write_json_atomic(self, path: Path, value: BaseModel | dict[str, Any] | list[Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self._payload(value), ensure_ascii=False, indent=2) + "\n"
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            self._fsync_directory(path.parent)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise
        return path

    def _append_jsonl(self, name: str, value: BaseModel) -> None:
        path = self.project_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(value.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _read_jsonl(self, name: str, model: type[T]) -> list[T]:
        path = self.project_dir / name
        if not path.exists():
            return []
        records: list[T] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(model.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(f"invalid {name} record at line {line_number}: {exc}") from exc
        return records

    @staticmethod
    def _read_model(path: Path, model: type[T]) -> T | None:
        if not path.exists():
            return None
        return model.model_validate_json(path.read_text(encoding="utf-8"))

    def _save_immutable(self, path: Path, value: BaseModel, label: str) -> None:
        existing = self._read_model(path, type(value))
        if existing is not None:
            if (existing.model_dump(mode="json", exclude={"created_at"})
                    != value.model_dump(mode="json", exclude={"created_at"})):
                raise ValueError(f"{label} is immutable once written")
            return
        self._write_json_atomic(path, value)

    def create(self, spec: ResearchProjectSpec) -> bool:
        """Atomically reserve a project id; return False for an identical existing spec."""
        if spec.project_id != self.project_id:
            raise ValueError("project spec id does not match store project id")
        with self._lock:
            self.project_dir.mkdir(parents=True, exist_ok=True)
            path = self.project_dir / "project_spec.json"
            content = json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
            try:
                with path.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                self._fsync_directory(path.parent)
                return True
            except FileExistsError:
                existing = self.load_spec()
                if (existing is None
                        or existing.model_dump(mode="json", exclude={"created_at"})
                        != spec.model_dump(mode="json", exclude={"created_at"})):
                    raise ValueError("project spec is immutable once written")
                return False

    def load_spec(self) -> ResearchProjectSpec | None:
        return self._read_model(self.project_dir / "project_spec.json", ResearchProjectSpec)

    def save_plan(self, plan: ResearchPlan) -> None:
        if plan.project_id != self.project_id:
            raise ValueError("research plan project id does not match store project id")
        with self._lock:
            self._save_immutable(self.project_dir / "research_plan.json", plan, "research plan")

    def load_plan(self) -> ResearchPlan | None:
        return self._read_model(self.project_dir / "research_plan.json", ResearchPlan)

    def save_state(self, state: ProjectState) -> None:
        if state.project_id != self.project_id:
            raise ValueError("project state id does not match store project id")
        with self._lock:
            self._write_json_atomic(self.project_dir / "project_state.json", state)

    def load_state(self) -> ProjectState | None:
        return self._read_model(self.project_dir / "project_state.json", ProjectState)

    def save_work_item_result(self, result: WorkItemResult) -> None:
        item_id = self._safe_component(result.item_id, "work item id")
        with self._lock:
            self._write_json_atomic(self.project_dir / "work_items" / item_id / "result.json", result)

    def load_work_item_results(self) -> dict[str, WorkItemResult]:
        root = self.project_dir / "work_items"
        if not root.exists():
            return {}
        results: dict[str, WorkItemResult] = {}
        for path in sorted(root.glob("*/result.json")):
            item_id = self._safe_component(path.parent.name, "work item id")
            result = WorkItemResult.model_validate_json(path.read_text(encoding="utf-8"))
            if result.item_id != item_id:
                raise ValueError(f"work item result path/id mismatch: {item_id} != {result.item_id}")
            results[item_id] = result
        return results

    def append_event(
        self,
        event_type: str,
        state: str,
        work_item_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> ProjectEvent:
        if work_item_id is not None:
            work_item_id = self._safe_component(work_item_id, "work item id")
        with self._lock:
            events = self.read_events()
            event = ProjectEvent(
                sequence=(events[-1].sequence + 1) if events else 1,
                project_id=self.project_id,
                event_type=event_type,
                state=state,
                work_item_id=work_item_id,
                detail=detail or {},
            )
            self._append_jsonl("events.jsonl", event)
            return event

    def read_events(self) -> list[ProjectEvent]:
        return self._read_jsonl("events.jsonl", ProjectEvent)

    def append_assessment(self, record: AssessmentRecord) -> None:
        if record.project_id != self.project_id:
            raise ValueError("assessment project id does not match store project id")
        with self._lock:
            self._append_jsonl("assessments.jsonl", record)

    def read_assessments(self) -> list[AssessmentRecord]:
        return self._read_jsonl("assessments.jsonl", AssessmentRecord)

    def append_decision(self, record: DecisionEvent) -> None:
        if record.project_id != self.project_id:
            raise ValueError("decision project id does not match store project id")
        with self._lock:
            self._append_jsonl("decisions.jsonl", record)

    def read_decisions(self) -> list[DecisionEvent]:
        return self._read_jsonl("decisions.jsonl", DecisionEvent)

    @contextmanager
    def execution_lock(self):
        """Hold a cross-instance process lock for one project's state transitions."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.project_dir / ".execution.lock"
        with lock_path.open("a+b") as handle:
            try:
                try:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    backend = "fcntl"
                except ImportError:  # pragma: no cover - Linux is the acceptance environment
                    import msvcrt
                    handle.seek(0)
                    if handle.tell() == 0:
                        handle.write(b"0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    backend = "msvcrt"
            except (BlockingIOError, OSError) as exc:
                raise ProjectBusyError(f"project is already executing: {self.project_id}") from exc
            try:
                yield
            finally:
                if backend == "fcntl":
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                else:  # pragma: no cover - Linux is the acceptance environment
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _resolved_project_file(self, path: Path | str) -> Path:
        resolved = Path(path).expanduser().resolve(strict=True)
        if not resolved.is_relative_to(self.project_dir):
            raise ValueError("artifact source must be inside the project directory")
        if not resolved.is_file():
            raise ValueError("artifact source must be a regular file")
        return resolved

    def register_artifact(
        self,
        path: Path | str,
        work_item_id: str,
        logical_name: str,
        media_type: str = "application/octet-stream",
    ) -> ArtifactRecord:
        work_item_id = self._safe_component(work_item_id, "work item id")
        if not logical_name.strip():
            raise ValueError("artifact logical name cannot be empty")
        source = self._resolved_project_file(path)
        artifact_root = self.project_dir / "artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)

        with self._lock:
            descriptor, temp_name = tempfile.mkstemp(prefix=".artifact.", suffix=".tmp", dir=artifact_root)
            os.close(descriptor)
            temp_path = Path(temp_name)
            try:
                shutil.copyfile(source, temp_path)
                with temp_path.open("rb") as handle:
                    os.fsync(handle.fileno())
                digest = self._sha256(temp_path)
                suffix = source.suffix if 0 < len(source.suffix) <= 20 else ""
                destination_dir = artifact_root / digest[:2]
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / f"{digest}{suffix}"
                if destination.exists():
                    if self._sha256(destination) != digest:
                        raise ValueError("content-addressed artifact path has conflicting content")
                    temp_path.unlink()
                else:
                    os.replace(temp_path, destination)
                    self._fsync_directory(destination_dir)
            except BaseException:
                temp_path.unlink(missing_ok=True)
                raise

            records = self.read_artifacts()
            matching = [
                item for item in records
                if item.work_item_id == work_item_id and item.logical_name == logical_name
            ]
            for existing in reversed(matching):
                if existing.sha256 == digest:
                    return existing
            record = ArtifactRecord(
                project_id=self.project_id,
                work_item_id=work_item_id,
                logical_name=logical_name,
                uri=f"project://{destination.relative_to(self.project_dir).as_posix()}",
                media_type=media_type,
                sha256=digest,
                size_bytes=destination.stat().st_size,
                version=max((item.version for item in matching), default=0) + 1,
            )
            self._append_jsonl("artifacts.jsonl", record)
            return record

    def read_artifacts(self) -> list[ArtifactRecord]:
        return self._read_jsonl("artifacts.jsonl", ArtifactRecord)

    def artifact_path(self, record: ArtifactRecord) -> Path:
        if record.project_id != self.project_id:
            raise ValueError("artifact belongs to a different project")
        relative = record.uri.removeprefix("project://")
        if not relative or Path(relative).is_absolute():
            raise ValueError("invalid project artifact URI")
        resolved = (self.project_dir / relative).resolve()
        if not resolved.is_relative_to(self.project_dir):
            raise ValueError("artifact URI escapes project directory")
        return resolved

    @staticmethod
    def _unique(records: list[BaseModel], field: str, label: str) -> None:
        values = [getattr(record, field) for record in records]
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {label} identifiers")

    def assert_integrity(self) -> None:
        spec = self.load_spec()
        if spec is None:
            raise ValueError("project spec is missing")
        if spec.project_id != self.project_id:
            raise ValueError("project spec id mismatch")

        plan = self.load_plan()
        if plan is not None and plan.project_id != self.project_id:
            raise ValueError("research plan project id mismatch")
        known_items = {item.item_id for item in plan.items} if plan is not None else set()

        state = self.load_state()
        if state is not None:
            if state.project_id != self.project_id:
                raise ValueError("project state id mismatch")
            referenced = set(state.completed_items) | set(state.failed_items) | set(state.attempts)
            if state.current_item_id:
                referenced.add(state.current_item_id)
            if known_items and not referenced.issubset(known_items):
                raise ValueError(f"project state references unknown work items: {sorted(referenced - known_items)}")

        results = self.load_work_item_results()
        if known_items and not set(results).issubset(known_items):
            raise ValueError(f"results reference unknown work items: {sorted(set(results) - known_items)}")

        events = self.read_events()
        expected_sequences = list(range(1, len(events) + 1))
        if [event.sequence for event in events] != expected_sequences:
            raise ValueError("project event sequence is not contiguous and monotonic")
        for event in events:
            if event.project_id != self.project_id:
                raise ValueError("project event id mismatch")
            if known_items and event.work_item_id and event.work_item_id not in known_items:
                raise ValueError(f"event references unknown work item: {event.work_item_id}")

        assessments = self.read_assessments()
        decisions = self.read_decisions()
        artifacts = self.read_artifacts()
        self._unique(assessments, "assessment_id", "assessment")
        self._unique(decisions, "decision_id", "decision")
        self._unique(artifacts, "artifact_id", "artifact")
        for record in [*assessments, *decisions, *artifacts]:
            if record.project_id != self.project_id:
                raise ValueError("append-only record project id mismatch")

        artifact_ids = {record.artifact_id for record in artifacts}
        assessment_ids = {record.assessment_id for record in assessments}
        allowed_decision_targets = known_items | artifact_ids | assessment_ids
        if plan is not None:
            allowed_decision_targets |= {plan.plan_id, f"release:{plan.plan_id}"}
        for decision in decisions:
            unknown_targets = set(decision.target_ids) - allowed_decision_targets
            if unknown_targets:
                raise ValueError(f"decision references unknown targets: {sorted(unknown_targets)}")
        for assessment in assessments:
            if assessment.target_id not in known_items | artifact_ids:
                raise ValueError(f"assessment references unknown target: {assessment.target_id}")
        for result in results.values():
            missing = set(result.artifact_ids) - artifact_ids
            if missing:
                raise ValueError(f"work item {result.item_id} references missing artifacts: {sorted(missing)}")

        for record in artifacts:
            if known_items and record.work_item_id not in known_items:
                raise ValueError(f"artifact references unknown work item: {record.work_item_id}")
            path = self.artifact_path(record)
            if not path.exists() or not path.is_file():
                raise ValueError(f"artifact file is missing: {record.artifact_id}")
            if path.stat().st_size != record.size_bytes:
                raise ValueError(f"artifact size mismatch: {record.artifact_id}")
            if self._sha256(path) != record.sha256:
                raise ValueError(f"artifact digest mismatch: {record.artifact_id}")


__all__ = ["ProjectBusyError", "ResearchProjectStore"]
