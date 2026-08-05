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
    AssessmentResult,
    AutonomyMode,
    DecisionEvent,
    FailureClass,
    DomainActivityRecord,
    ProjectEvent,
    ProjectState,
    RepairAction,
    RepairAuthorization,
    RepairRequest,
    RepairResolution,
    RepairResolutionStatus,
    ResearchPlan,
    ResearchPlanRevision,
    ResearchProjectSpec,
    WorkItemResult,
    WorkItemStatus,
)
from .research_projection import DomainActivityProjection, trace_event_digest
from .research_repair import (
    active_assessments,
    canonical_sha256,
    effective_plan,
    project_snapshot_digest,
    work_item_result_digest,
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

    def append_repair_request(self, request: RepairRequest) -> None:
        if request.project_id != self.project_id:
            raise ValueError("repair request project id does not match store project id")
        request_id = self._safe_component(request.repair_request_id, "repair request id")
        with self._lock:
            self._save_immutable(
                self.project_dir / "repair_requests" / f"{request_id}.json",
                request,
                "repair request",
            )

    def read_repair_requests(self) -> list[RepairRequest]:
        root = self.project_dir / "repair_requests"
        if not root.exists():
            return []
        return sorted(
            (RepairRequest.model_validate_json(path.read_text(encoding="utf-8")) for path in root.glob("*.json")),
            key=lambda row: (row.created_at, row.repair_request_id),
        )

    def append_plan_revision(self, revision: ResearchPlanRevision) -> None:
        if revision.project_id != self.project_id:
            raise ValueError("plan revision project id does not match store project id")
        revision_id = self._safe_component(revision.revision_id, "plan revision id")
        with self._lock:
            existing = self.read_plan_revisions()
            same_number = next((row for row in existing if row.revision_number == revision.revision_number), None)
            if same_number is not None and same_number.revision_id != revision.revision_id:
                raise ValueError("plan revision number already has different immutable content")
            self._save_immutable(
                self.project_dir / "plan_revisions" / f"{revision_id}.json",
                revision,
                "plan revision",
            )

    def read_plan_revisions(self) -> list[ResearchPlanRevision]:
        root = self.project_dir / "plan_revisions"
        if not root.exists():
            return []
        return sorted(
            (ResearchPlanRevision.model_validate_json(path.read_text(encoding="utf-8"))
             for path in root.glob("*.json")),
            key=lambda row: row.revision_number,
        )

    def load_effective_plan(self) -> ResearchPlan | None:
        base = self.load_plan()
        return effective_plan(base, self.read_plan_revisions()) if base is not None else None

    def append_repair_resolution(self, resolution: RepairResolution) -> None:
        if resolution.project_id != self.project_id:
            raise ValueError("repair resolution project id does not match store project id")
        resolution_id = self._safe_component(resolution.resolution_id, "repair resolution id")
        with self._lock:
            self._save_immutable(
                self.project_dir / "repair_resolutions" / f"{resolution_id}.json",
                resolution,
                "repair resolution",
            )

    def read_repair_resolutions(self) -> list[RepairResolution]:
        root = self.project_dir / "repair_resolutions"
        if not root.exists():
            return []
        return sorted(
            (RepairResolution.model_validate_json(path.read_text(encoding="utf-8"))
             for path in root.glob("*.json")),
            key=lambda row: (row.created_at, row.resolution_id),
        )

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

    def append_domain_activity(self, projection: DomainActivityProjection) -> DomainActivityRecord:
        """Assign sequence and append one child-trace projection idempotently."""
        project_id = str(projection.values.get("project_id") or "")
        work_item_id = str(projection.values.get("work_item_id") or "")
        child_run_id = str(projection.values.get("child_run_id") or "")
        source_trace_id = str(projection.values.get("source_trace_id") or "")
        if project_id != self.project_id:
            raise ValueError("domain activity project id does not match store project id")
        self._safe_component(work_item_id, "work item id")
        self._safe_component(child_run_id, "child run id")
        with self._lock:
            existing = next(
                (
                    row for row in self.read_domain_activities()
                    if row.child_run_id == child_run_id and row.source_trace_id == source_trace_id
                ),
                None,
            )
            if existing is not None:
                if existing != projection.to_record(existing.sequence):
                    raise ValueError("source trace id has a conflicting domain activity projection")
                return existing
            record = projection.to_record(len(self.read_domain_activities()) + 1)
            self._append_jsonl("domain_activities.jsonl", record)
            return record

    def read_domain_activities(
        self,
        after_sequence: int = 0,
        limit: int | None = None,
        work_item_id: str | None = None,
    ) -> list[DomainActivityRecord]:
        if after_sequence < 0:
            raise ValueError("after_sequence must be non-negative")
        if limit is not None and not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if work_item_id is not None:
            work_item_id = self._safe_component(work_item_id, "work item id")
        records = [
            row for row in self._read_jsonl("domain_activities.jsonl", DomainActivityRecord)
            if row.sequence > after_sequence and (work_item_id is None or row.work_item_id == work_item_id)
        ]
        return records[:limit] if limit is not None else records

    def domain_activity_cursor(self) -> int:
        records = self._read_jsonl("domain_activities.jsonl", DomainActivityRecord)
        return records[-1].sequence if records else 0

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

        base_plan = self.load_plan()
        if base_plan is not None and base_plan.project_id != self.project_id:
            raise ValueError("research plan project id mismatch")
        repair_requests = self.read_repair_requests()
        revisions = self.read_plan_revisions()
        resolutions = self.read_repair_resolutions()
        plan = effective_plan(base_plan, revisions) if base_plan is not None else None
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

        artifacts = self.read_artifacts()
        activities = self.read_domain_activities()
        expected_activity_sequences = list(range(1, len(activities) + 1))
        if [activity.sequence for activity in activities] != expected_activity_sequences:
            raise ValueError("domain activity sequence is not contiguous and monotonic")
        self._unique(activities, "activity_id", "domain activity")
        self._unique(activities, "source_trace_id", "domain activity source trace")
        trace_events_by_run: dict[str, dict[str, str]] = {}
        for artifact in artifacts:
            if artifact.logical_name != "target_discovery_trace":
                continue
            path = self.artifact_path(artifact)
            if not path.is_file():
                continue
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    run_id = str(payload.get("run_id") or "")
                    event_id = str(payload.get("event_id") or "")
                    if run_id and event_id:
                        trace_events_by_run.setdefault(run_id, {})[event_id] = trace_event_digest(payload)
        for activity in activities:
            if activity.project_id != self.project_id:
                raise ValueError("domain activity project id mismatch")
            if known_items and activity.work_item_id not in known_items:
                raise ValueError(f"domain activity references unknown work item: {activity.work_item_id}")
            run_id = self._safe_component(activity.child_run_id, "child run id")
            if run_id not in trace_events_by_run:
                raise ValueError(f"domain activity source trace artifact is missing: {run_id}")
            source_digest = trace_events_by_run[run_id].get(activity.source_trace_id)
            if source_digest is None:
                raise ValueError(
                    f"domain activity references missing source trace: {activity.source_trace_id}"
                )
            if source_digest != activity.source_event_sha256:
                raise ValueError(
                    f"domain activity source digest mismatch: {activity.source_trace_id}"
                )

        assessments = self.read_assessments()
        decisions = self.read_decisions()
        self._unique(assessments, "assessment_id", "assessment")
        self._unique(decisions, "decision_id", "decision")
        self._unique(artifacts, "artifact_id", "artifact")
        self._unique(repair_requests, "repair_request_id", "repair request")
        self._unique(revisions, "revision_id", "plan revision")
        self._unique(resolutions, "resolution_id", "repair resolution")
        for record in [*assessments, *decisions, *artifacts, *repair_requests, *revisions, *resolutions]:
            if record.project_id != self.project_id:
                raise ValueError("append-only record project id mismatch")

        artifact_ids = {record.artifact_id for record in artifacts}
        assessment_ids = {record.assessment_id for record in assessments}
        request_ids = {record.repair_request_id for record in repair_requests}
        revision_ids = {record.revision_id for record in revisions}
        allowed_decision_targets = known_items | artifact_ids | assessment_ids | request_ids | revision_ids
        if base_plan is not None:
            allowed_decision_targets.add(base_plan.plan_id)
        for decision in decisions:
            unknown_targets = {
                target for target in decision.target_ids
                if target not in allowed_decision_targets
                and not re.fullmatch(r"release:[0-9a-f]{64}", target)
            }
            if unknown_targets:
                raise ValueError(f"decision references unknown targets: {sorted(unknown_targets)}")
        for assessment in assessments:
            if assessment.target_id not in known_items | artifact_ids:
                raise ValueError(f"assessment references unknown target: {assessment.target_id}")
        for result in results.values():
            missing = set(result.artifact_ids) - artifact_ids
            if missing:
                raise ValueError(f"work item {result.item_id} references missing artifacts: {sorted(missing)}")

        request_by_id = {row.repair_request_id: row for row in repair_requests}
        revision_by_id = {row.revision_id: row for row in revisions}
        if [row.revision_number for row in revisions] != list(range(1, len(revisions) + 1)):
            raise ValueError("plan revision sequence is not contiguous")
        known_before = {item.item_id for item in base_plan.items} if base_plan is not None else set()
        prior_revision_id: str | None = None
        for revision in revisions:
            request = request_by_id.get(revision.repair_request_id)
            if request is None:
                raise ValueError("plan revision references missing repair request")
            if base_plan is None or revision.base_plan_id != base_plan.plan_id:
                raise ValueError("plan revision base plan mismatch")
            if revision.parent_revision_id != prior_revision_id:
                raise ValueError("plan revision parent chain is not contiguous")
            revision_body = {
                "project_id": revision.project_id,
                "base_plan_id": revision.base_plan_id,
                "parent_revision_id": revision.parent_revision_id,
                "revision_number": revision.revision_number,
                "repair_request_id": revision.repair_request_id,
                "operation": revision.operation,
                "added_items": [item.model_dump(mode="json") for item in revision.added_items],
                "superseded_item_ids": revision.superseded_item_ids,
                "superseded_assessment_ids": revision.superseded_assessment_ids,
                "trigger_snapshot_digest": revision.trigger_snapshot_digest,
                "approval_required": revision.approval_required,
            }
            if canonical_sha256(revision_body) != revision.revision_digest:
                raise ValueError("plan revision digest mismatch")
            if revision.trigger_snapshot_digest != request.trigger_snapshot_digest:
                raise ValueError("plan revision trigger snapshot mismatch")
            if request.failure_class != FailureClass.TRANSIENT or request.action != RepairAction.RERUN_SUBGRAPH_SAME_INPUTS:
                raise ValueError("plan revision is not backed by an eligible same-input transient request")
            expected_authorization = (
                RepairAuthorization.AUTOMATIC
                if spec.autonomy_mode == AutonomyMode.AUTONOMOUS
                else RepairAuthorization.CHECKPOINT_REQUIRED
            )
            if request.authorization != expected_authorization:
                raise ValueError("repair request authorization does not match project autonomy")
            if revision.approval_required != (expected_authorization == RepairAuthorization.CHECKPOINT_REQUIRED):
                raise ValueError("plan revision approval requirement does not match repair authorization")
            if revision.approval_required and not any(
                decision.action.value == "accept"
                and request.repair_request_id in decision.target_ids
                and decision.evidence_snapshot_digest == request.trigger_snapshot_digest
                for decision in decisions
            ):
                raise ValueError("checkpointed plan revision lacks exact-snapshot approval")
            if any(
                decision.action.value == "reject"
                and request.repair_request_id in decision.target_ids
                and decision.evidence_snapshot_digest == request.trigger_snapshot_digest
                for decision in decisions
            ):
                raise ValueError("plan revision conflicts with an immutable repair rejection")
            if not set(revision.superseded_item_ids).issubset(known_before):
                raise ValueError("plan revision supersedes unknown work items")
            if revision.superseded_item_ids != request.affected_work_item_ids:
                raise ValueError("plan revision affected work items do not match repair request")
            added_ids = {item.item_id for item in revision.added_items}
            if added_ids & known_before:
                raise ValueError("plan revision reuses an existing work item id")
            prior_items = {
                item.item_id: item
                for item in [*base_plan.items, *(added for prior in revisions
                                                 if prior.revision_number < revision.revision_number
                                                 for added in prior.added_items)]
            }
            replacement_by_source = {item.rerun_of_item_id: item for item in revision.added_items}
            if set(replacement_by_source) != set(revision.superseded_item_ids):
                raise ValueError("plan revision must replace every and only superseded work item")
            replacement_ids = {
                source_id: replacement.item_id for source_id, replacement in replacement_by_source.items()
            }
            for item in revision.added_items:
                if item.rerun_of_item_id not in revision.superseded_item_ids:
                    raise ValueError("revision item does not rerun a superseded work item")
                source = prior_items[item.rerun_of_item_id]
                source_payload = source.model_dump(mode="json", exclude={
                    "item_id", "dependencies", "rerun_of_item_id", "repair_request_id",
                })
                item_payload = item.model_dump(mode="json", exclude={
                    "item_id", "dependencies", "rerun_of_item_id", "repair_request_id",
                })
                if source_payload != item_payload:
                    raise ValueError("plan revision changes work-item content beyond retry metadata")
                expected_dependencies = [replacement_ids.get(dep, dep) for dep in source.dependencies]
                if item.dependencies != expected_dependencies:
                    raise ValueError("plan revision changes dependencies beyond the affected subgraph overlay")
            known_before |= added_ids
            prior_revision_id = revision.revision_id
        for request in repair_requests:
            source = results.get(request.target_work_item_id)
            if source is None or work_item_result_digest(source) != request.trigger_result_digest:
                raise ValueError("repair request source result digest mismatch")
            if (source.status != WorkItemStatus.FAILED
                    or source.failure_class != FailureClass.TRANSIENT
                    or source.input_digest != request.input_digest):
                raise ValueError("repair request source is not an identical-input transient failure")
            if not set(request.trigger_assessment_ids).issubset(assessment_ids):
                raise ValueError("repair request references missing trigger assessment")
            trigger_assessments = [
                row for row in assessments if row.assessment_id in request.trigger_assessment_ids
            ]
            if any(
                row.target_id != request.target_work_item_id
                or row.target_digest != request.trigger_result_digest
                or row.result != AssessmentResult.FAIL
                or not row.blocking
                or row.method != "typed_status_gate"
                or row.actor not in {"independent_review", "fake_independent_review"}
                for row in trigger_assessments
            ):
                raise ValueError("repair request trigger assessment is not a bound blocking status failure")
        for resolution in resolutions:
            if resolution.repair_request_id not in request_ids or resolution.revision_id not in revision_by_id:
                raise ValueError("repair resolution references missing request or revision")
            if not set(resolution.verification_assessment_ids).issubset(assessment_ids):
                raise ValueError("repair resolution references missing verification assessment")
            request = request_by_id[resolution.repair_request_id]
            revision = revision_by_id[resolution.revision_id]
            if resolution.before_snapshot_digest != request.trigger_snapshot_digest:
                raise ValueError("repair resolution before snapshot mismatch")
            root = next(
                item for item in revision.added_items
                if item.rerun_of_item_id == request.target_work_item_id
            )
            root_result = results.get(root.item_id)
            verification = [
                row for row in assessments
                if row.assessment_id in resolution.verification_assessment_ids
            ]
            verified = (
                root_result is not None
                and any(
                    row.target_id == root.item_id
                    and row.target_digest == work_item_result_digest(root_result)
                    and row.result == AssessmentResult.PASS
                    and not row.blocking
                    and row.method == "typed_status_gate"
                    and row.actor in {"independent_review", "fake_independent_review"}
                    for row in verification
                )
            )
            if resolution.status == RepairResolutionStatus.RESOLVED:
                if not verified or root_result.input_digest != request.input_digest:
                    raise ValueError("resolved repair lacks identical-input independent verification")
                if any(
                    results.get(item.item_id) is None
                    or results[item.item_id].status != WorkItemStatus.COMPLETED
                    for item in revision.added_items
                ):
                    raise ValueError("resolved repair contains an incomplete recomputed work item")
        if resolutions:
            latest = max(resolutions, key=lambda row: revision_by_id[row.revision_id].revision_number)
            if revision_by_id[latest.revision_id].revision_number == len(revisions):
                current_snapshot = project_snapshot_digest(
                    plan=plan,
                    results=results,
                    assessments=assessments,
                    artifacts=artifacts,
                    revisions=revisions,
                )
                if latest.after_snapshot_digest != current_snapshot:
                    raise ValueError("latest repair resolution after snapshot mismatch")

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
