"""Typed research modules used by the project-level orchestrator.

Modules may call networks or domain runtimes, but they cannot execute arbitrary
model-generated code. Every module returns a typed result and files that the
project store subsequently hashes and registers.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .contracts import TaskSpec, ToolDescriptor, TraceEvent
from .llm import LLMUnavailable, StepClient
from .research_contracts import (
    ArtifactRecord, AssessmentDimension, AssessmentLevel, AssessmentRecord,
    AssessmentResult, FailureClass, ResearchProjectSpec, WorkItemResult, WorkItemSpec,
    WorkItemStatus,
)
from .research_projection import DomainActivityProjection, project_trace_event
from .research_repair import classify_exception, work_item_result_digest
from .settings import Settings


EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


@dataclass(frozen=True)
class ModuleDescriptor:
    name: str
    description: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    execution_policy: str
    network_access: bool = False
    supports_resume: bool = True
    side_effect_free: bool = False
    replay_safe: bool = False
    repair_modes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PendingArtifact:
    path: Path
    logical_name: str
    media_type: str


@dataclass
class ModuleContext:
    project: ResearchProjectSpec
    item: WorkItemSpec
    project_dir: Path
    cache_dir: Path
    settings: Settings
    prior_results: dict[str, WorkItemResult] = field(default_factory=dict)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    activity_sink: Callable[[DomainActivityProjection], None] | None = None

    @property
    def output_dir(self) -> Path:
        path = self.project_dir / "work_items" / self.item.item_id / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifact_path(self, artifact: ArtifactRecord) -> Path:
        prefix = "project://"
        if not artifact.uri.startswith(prefix):
            raise ValueError("artifact does not use a project URI")
        candidate = (self.project_dir / artifact.uri[len(prefix):]).resolve()
        root = self.project_dir.resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("artifact URI escapes project directory")
        return candidate


@dataclass
class ModuleExecution:
    result: WorkItemResult
    artifacts: list[PendingArtifact] = field(default_factory=list)
    assessments: list[AssessmentRecord] = field(default_factory=list)


class ResearchModule(Protocol):
    descriptor: ModuleDescriptor

    def execute(self, context: ModuleContext) -> ModuleExecution: ...


class ResearchModuleRegistry:
    def __init__(self, modules: list[ResearchModule] | None = None):
        self._modules: dict[str, ResearchModule] = {}
        for module in modules or []:
            self.register(module)

    def register(self, module: ResearchModule) -> None:
        name = module.descriptor.name
        if name in self._modules:
            raise ValueError(f"duplicate research module: {name}")
        self._modules[name] = module

    def get(self, name: str) -> ResearchModule:
        try:
            return self._modules[name]
        except KeyError as exc:
            raise KeyError(f"research module is not registered: {name}") from exc

    @property
    def names(self) -> list[str]:
        return sorted(self._modules)

    def public_capabilities(self) -> list[dict[str, Any]]:
        return [self._modules[name].descriptor.__dict__.copy() for name in self.names]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _result(item: WorkItemSpec, status: WorkItemStatus, summary: str, **kwargs: Any) -> WorkItemResult:
    return WorkItemResult(item_id=item.item_id, module=item.module, status=status, summary=summary, **kwargs)


class ProjectBriefModule:
    descriptor = ModuleDescriptor(
        name="project_brief",
        description="Freeze the original goal, constraints, success criteria and expected deliverables.",
        input_types=("ResearchProjectSpec",), output_types=("ProjectBrief",),
        execution_policy="deterministic_local", side_effect_free=True, replay_safe=True,
    )

    def execute(self, context: ModuleContext) -> ModuleExecution:
        goal = context.project.goal
        lines = [
            f"# {context.project.title}", "", "## Research question", "", goal.question, "",
            "## Success criteria", "", *[f"- {value}" for value in goal.success_criteria], "",
            "## Deliverables", "", *[f"- {value}" for value in goal.deliverables], "",
            "## Constraints", "", *([f"- {value}" for value in goal.constraints] or ["- None declared"]), "",
            "## Execution policy", "", f"- Autonomy mode: `{context.project.autonomy_mode.value}`",
            "- The root goal is immutable during an approved plan; scope changes require a DecisionEvent.", "",
        ]
        path = context.output_dir / "project_brief.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return ModuleExecution(
            result=_result(context.item, WorkItemStatus.COMPLETED, "Research goal and completion contract frozen.",
                           outputs={"question": goal.question, "deliverables": goal.deliverables,
                                    "success_criteria": goal.success_criteria}),
            artifacts=[PendingArtifact(path, "project_brief", "text/markdown")],
        )


class LiteratureSearchModule:
    descriptor = ModuleDescriptor(
        name="literature_search",
        description="Search Europe PMC and preserve source identifiers; retrieval hits are not treated as validated claims.",
        input_types=("ResearchGoal",), output_types=("LiteratureRecord[]",),
        execution_policy="read_only_connector", network_access=True,
        side_effect_free=True, replay_safe=True, repair_modes=("same_input_retry",),
    )

    def __init__(self, session: requests.Session | None = None, page_size: int = 15):
        self.session = session
        self.page_size = min(max(page_size, 1), 50)

    def execute(self, context: ModuleContext) -> ModuleExecution:
        query = str(context.item.inputs.get("query") or context.project.context.get("literature_query")
                    or context.project.goal.question).strip()
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        cache_path = context.cache_dir / "research_literature" / f"{digest}.json"
        from_cache = False
        try:
            if context.settings.cache_only:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                from_cache = True
            else:
                session = self.session or requests.Session()
                response = session.get(
                    EUROPE_PMC_SEARCH,
                    params={"query": query, "format": "json", "pageSize": self.page_size, "resultType": "core"},
                    timeout=(10, 45),
                )
                response.raise_for_status()
                payload = response.json()
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                _write_json(cache_path, payload)
        except (OSError, ValueError, requests.RequestException) as exc:
            if cache_path.exists():
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                from_cache = True
            else:
                return ModuleExecution(result=_result(
                    context.item, WorkItemStatus.NEEDS_INPUT,
                    "Literature retrieval was unavailable and no source-bound cache exists.",
                    outputs={"query": query, "record_count": 0, "retrieval_hits_are_claims": False},
                    limitations=["No literature records were available for evidence-grounded synthesis."],
                    error=exc.__class__.__name__,
                ))
        records: list[dict[str, Any]] = []
        for row in payload.get("resultList", {}).get("result", []):
            source_id = row.get("pmid") or row.get("pmcid") or row.get("doi") or row.get("id")
            if not source_id:
                continue
            journal_info = row.get("journalInfo") or {}
            records.append({
                "source_id": str(source_id),
                "pmid": row.get("pmid"), "pmcid": row.get("pmcid"), "doi": row.get("doi"),
                "title": row.get("title") or "", "abstract": row.get("abstractText") or "",
                "publication_date": row.get("firstPublicationDate") or journal_info.get("printPublicationDate"),
                "source_url": f"https://europepmc.org/article/MED/{row['pmid']}" if row.get("pmid")
                              else f"https://europepmc.org/article/PMC/{row['pmcid']}" if row.get("pmcid") else None,
            })
        output_path = context.output_dir / "literature_records.json"
        _write_json(output_path, {"query": query, "from_cache": from_cache, "records": records})
        status = WorkItemStatus.COMPLETED if records else WorkItemStatus.COMPLETED_WITH_GAPS
        limitations = [] if records else ["The search returned no citable records; query refinement is required."]
        return ModuleExecution(
            result=_result(context.item, status, f"Retrieved {len(records)} source-indexed literature records.",
                           outputs={"query": query, "record_count": len(records),
                                    "source_ids": [row["source_id"] for row in records],
                                    "retrieval_hits_are_claims": False, "from_cache": from_cache},
                           evidence_refs=[row["source_url"] for row in records if row.get("source_url")],
                           limitations=limitations),
            artifacts=[PendingArtifact(output_path, "literature_records", "application/json")],
        )


class _Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=5)
    rationale: str = Field(min_length=5)
    source_ids: list[str] = Field(min_length=1)
    falsification_test: str = Field(min_length=5)
    assumptions: list[str] = Field(default_factory=list)


class _HypothesisPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hypotheses: list[_Hypothesis]


class HypothesisGenerationModule:
    descriptor = ModuleDescriptor(
        name="hypothesis_generation",
        description="Generate falsifiable hypotheses grounded only in retrieved source records.",
        input_types=("LiteratureRecord[]",), output_types=("Hypothesis[]",),
        execution_policy="structured_llm", side_effect_free=True, replay_safe=True,
    )

    def __init__(self, client: StepClient | None):
        self.client = client

    def execute(self, context: ModuleContext) -> ModuleExecution:
        record_artifact = next((item for item in reversed(context.artifacts)
                                if item.logical_name == "literature_records"), None)
        if record_artifact is None:
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "No literature artifact is available for grounded hypothesis generation.",
                limitations=["Hypotheses were not generated because their source boundary is missing."],
            ))
        payload = json.loads(context.artifact_path(record_artifact).read_text(encoding="utf-8"))
        records = payload.get("records", [])
        if not records:
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "No retrieved records support hypothesis generation.",
                limitations=["Refused to invent hypotheses without source records."],
            ))
        if self.client is None:
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "A structured LLM reviewer is not configured.",
                outputs={"available_source_ids": [row["source_id"] for row in records]},
                limitations=["No deterministic fallback fabricates scientific hypotheses."],
            ))
        compact = [{"source_id": row["source_id"], "title": row["title"], "abstract": row["abstract"][:2000]}
                   for row in records[:12]]
        system = (
            "Generate up to five falsifiable life-science hypotheses using only the supplied records. "
            "Return JSON {hypotheses:[{statement,rationale,source_ids,falsification_test,assumptions}]}. "
            "Every source_id must be copied from the input. Separate observations from inference and do not add facts."
        )
        try:
            raw = self.client.json_completion(system, json.dumps({
                "question": context.project.goal.question, "records": compact,
            }, ensure_ascii=False))
            hypotheses = _HypothesisPayload.model_validate(raw).hypotheses
        except (LLMUnavailable, ValidationError, TypeError, ValueError) as exc:
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "Structured hypothesis generation failed validation.",
                limitations=["No invalid or ungrounded hypothesis was accepted."], error=exc.__class__.__name__,
            ))
        allowed = {row["source_id"] for row in records}
        valid = [hypothesis for hypothesis in hypotheses if set(hypothesis.source_ids) <= allowed]
        rejected = len(hypotheses) - len(valid)
        if not valid:
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "All generated hypotheses failed source-id alignment.",
                outputs={"rejected_hypotheses": rejected},
                limitations=["No hypothesis passed the source alignment gate."],
            ))
        output_path = context.output_dir / "hypotheses.json"
        _write_json(output_path, {"hypotheses": [item.model_dump(mode="json") for item in valid],
                                  "rejected_hypotheses": rejected})
        return ModuleExecution(
            result=_result(context.item, WorkItemStatus.COMPLETED, f"Generated {len(valid)} source-aligned hypotheses.",
                           outputs={"hypothesis_count": len(valid), "rejected_hypotheses": rejected,
                                    "hypotheses": [item.model_dump(mode="json") for item in valid]},
                           evidence_refs=sorted({source for item in valid for source in item.source_ids})),
            artifacts=[PendingArtifact(output_path, "hypotheses", "application/json")],
        )


def _apply_dataset_override(
    raw_task: Any,
    override: Any,
) -> Any:
    """Merge a typed dataset-switch override without changing frozen biological context."""
    if not isinstance(raw_task, dict) or not isinstance(override, dict):
        return raw_task
    merged = json.loads(json.dumps(raw_task))
    constraints = dict(merged.get("constraints") or {})
    selection = dict(constraints.get("dataset_selection") or {})
    if isinstance(override.get("preferred_dataset_accessions"), list):
        selection["preferred_dataset_accessions"] = override["preferred_dataset_accessions"]
    if isinstance(override.get("excluded_dataset_accessions"), list):
        selection["excluded_dataset_accessions"] = override["excluded_dataset_accessions"]
    constraints["dataset_selection"] = selection
    merged["constraints"] = constraints
    return merged


class TargetDiscoveryModule:
    descriptor = ModuleDescriptor(
        name="target_discovery",
        description="Run the existing traceable disease-target workflow as a bounded domain module.",
        input_types=("TaskSpec@2.2.0",), output_types=("TargetCard[]", "DiseaseTargetReport"),
        execution_policy="typed_domain_workflow", network_access=True,
        side_effect_free=True, replay_safe=True,
        repair_modes=("same_input_retry", "alternate_dataset"),
    )

    def execute(self, context: ModuleContext) -> ModuleExecution:
        raw_task = context.item.inputs.get("target_task_spec", context.project.context.get("target_task_spec"))
        raw_task = _apply_dataset_override(raw_task, context.item.inputs.get("dataset_override"))
        if not isinstance(raw_task, dict):
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "The disease-target workflow requires a target_task_spec.",
                limitations=["No target_task_spec was supplied; the vertical workflow was not executed."],
            ))
        try:
            from .legacy import parse_task_spec
            task = parse_task_spec(raw_task)
        except ValidationError as exc:
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "The target-discovery input contract is invalid.",
                error="TaskSpecValidationError", limitations=[str(exc.errors(include_url=False))],
            ))
        except ValueError as exc:
            return ModuleExecution(result=_result(
                context.item, WorkItemStatus.NEEDS_INPUT, "The target-discovery input contract is invalid.",
                error="TaskSpecVersionError", limitations=[str(exc)],
            ))
        from .runtime_langgraph import LangGraphRuntime

        child_run_id = f"target-{context.project.project_id}"
        if context.item.rerun_of_item_id is not None:
            child_run_id = f"{child_run_id}-{context.item.item_id}"
        run_dir = context.project_dir / "domain_runs" / child_run_id
        runtime = LangGraphRuntime(
            runs_dir=context.project_dir / "domain_runs", cache_dir=context.cache_dir, settings=context.settings,
            trace_observer=lambda event: self._record_trace(
                context, child_run_id, runtime.registry.descriptors, event,
            ),
        )
        if context.activity_sink is not None and run_dir.exists():
            from .store import EvidenceStore
            for event in EvidenceStore(run_dir).traces():
                try:
                    self._record_trace(context, child_run_id, runtime.registry.descriptors, event)
                except Exception:
                    # A full post-run reconciliation determines projection completeness.
                    pass
        child_error: str | None = None
        child_failure_class: FailureClass | None = None
        try:
            status = runtime.run(task, run_id=child_run_id, resume=run_dir.exists())
        except Exception as exc:
            # Preserve any already-durable child Trace and degrade the project item.
            child_error = exc.__class__.__name__
            child_failure_class = classify_exception(exc)
            status = {"terminal_status": "failed"}
        terminal = status.get("terminal_status")
        mapped = {
            "completed": WorkItemStatus.COMPLETED,
            "completed_with_gaps": WorkItemStatus.COMPLETED_WITH_GAPS,
            "needs_input": WorkItemStatus.NEEDS_INPUT,
            "failed": WorkItemStatus.FAILED,
            "refused": WorkItemStatus.FAILED,
        }.get(terminal, WorkItemStatus.FAILED)
        projection_errors: list[str] = []
        if context.activity_sink is not None:
            from .store import EvidenceStore
            for event in EvidenceStore(run_dir).traces():
                try:
                    self._record_trace(context, child_run_id, runtime.registry.descriptors, event)
                except Exception as exc:
                    projection_errors.append(exc.__class__.__name__)
        ranked_path = run_dir / "ranked_targets.json"
        cards_path = run_dir / "target_cards.json"
        report_path = run_dir / "report.md"
        try:
            ranked_rows = json.loads(ranked_path.read_text(encoding="utf-8")) if ranked_path.is_file() else []
            card_rows = json.loads(cards_path.read_text(encoding="utf-8")) if cards_path.is_file() else []
        except (OSError, json.JSONDecodeError):
            ranked_rows, card_rows = [], []
        ranked_count = len(ranked_rows) if isinstance(ranked_rows, list) else 0
        card_count = len(card_rows) if isinstance(card_rows, list) else 0
        experiment_count = (sum(isinstance(row, dict) and isinstance(row.get("experiment_plan"), dict)
                                for row in card_rows) if isinstance(card_rows, list) else 0)
        deliverables_complete = bool(
            report_path.is_file() and ranked_count > 0 and card_count > 0 and experiment_count == card_count
        )
        if mapped == WorkItemStatus.COMPLETED and not deliverables_complete:
            mapped = WorkItemStatus.COMPLETED_WITH_GAPS
        scientific_complete = mapped == WorkItemStatus.COMPLETED
        projection_complete = not projection_errors
        if mapped == WorkItemStatus.COMPLETED and not projection_complete:
            mapped = WorkItemStatus.COMPLETED_WITH_GAPS
        pending: list[PendingArtifact] = []
        for filename, logical, media in (
            ("report.md", "target_discovery_report", "text/markdown"),
            ("ranked_targets.json", "ranked_targets", "application/json"),
            ("target_cards.json", "target_cards", "application/json"),
            ("trace.jsonl", "target_discovery_trace", "application/x-ndjson"),
            ("tool_results.jsonl", "target_discovery_tool_results", "application/x-ndjson"),
            ("evidence_items.jsonl", "target_discovery_evidence", "application/x-ndjson"),
            ("claims.jsonl", "target_discovery_claims", "application/x-ndjson"),
            ("reviewer_findings.jsonl", "target_discovery_reviewer_findings", "application/x-ndjson"),
            ("execution_plan.json", "target_discovery_execution_plan", "application/json"),
            ("task_spec.json", "target_discovery_task_spec", "application/json"),
            ("case_record.json", "target_discovery_case_record", "application/json"),
            ("status.json", "target_discovery_status", "application/json"),
        ):
            path = run_dir / filename
            if path.exists():
                pending.append(PendingArtifact(path, logical, media))
        return ModuleExecution(
            result=_result(context.item, mapped, f"Target-discovery workflow ended with {terminal}.",
                           outputs={
                               "child_run_id": child_run_id, "terminal_status": terminal,
                               "ranked_target_count": ranked_count, "target_card_count": card_count,
                               "experiment_plan_count": experiment_count,
                               "deliverables_complete": deliverables_complete,
                               "domain_activity_projection_complete": projection_complete,
                               "dataset_candidates": self._read_dataset_candidates(run_dir),
                           },
                           error=child_error,
                           failure_class=child_failure_class or (
                               FailureClass.SCIENTIFIC_GAP
                               if mapped == WorkItemStatus.COMPLETED_WITH_GAPS
                               else None
                           ),
                           limitations=([] if scientific_complete else [
                               "The domain workflow has evidence gaps or is missing ranking, TargetCard, experiment, or report artifacts."
                           ]) + ([] if projection_complete else [
                               "One or more child TraceEvents could not be indexed in the project activity ledger; the child trace remains authoritative."
                           ]) + ([] if child_error is None else [
                               "The child runtime raised an unexpected error after preserving its durable trace."
                           ])),
            artifacts=pending,
        )

    @staticmethod
    def _read_dataset_candidates(run_dir: Path) -> list[dict[str, Any]]:
        """Normalize dataset-selection rows from durable child-run records.

        Preferred source is the typed ``geo_metadata_audit`` tool result
        (audited_datasets plus selection_trace); ``report.json`` is a fallback.
        Rows always carry an accession and a normalized status so the project
        repair policy can distinguish rejected from eligible candidates.
        """
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add(row: dict[str, Any]) -> None:
            accession = str(row.get("accession") or row.get("dataset_id") or "").strip()
            if not accession or accession in seen:
                return
            seen.add(accession)
            candidates.append(row)

        def selection_status(row: dict[str, Any]) -> str:
            raw = str(row.get("status") or row.get("qualification") or "").lower()
            if raw in {"candidate", "qualified", "eligible", "available", "selected"}:
                return "candidate"
            if raw in {"rejected", "ineligible", "unqualified", "eligible_not_selected_limit"}:
                return "rejected"
            decision = str(row.get("decision") or "").lower()
            if decision in {"selected", "eligible_not_selected_limit"}:
                return "candidate"
            if decision == "rejected":
                return "rejected"
            nested = row.get("candidate")
            if isinstance(nested, dict):
                return "candidate" if str(nested.get("eligibility") or "").lower() == "eligible" else "rejected"
            return "rejected"

        tool_results_path = run_dir / "tool_results.jsonl"
        try:
            if tool_results_path.is_file():
                for line in tool_results_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict) or row.get("tool_name") != "geo_metadata_audit":
                        continue
                    outputs = row.get("outputs") if isinstance(row.get("outputs"), dict) else {}
                    audited = outputs.get("audited_datasets")
                    if isinstance(audited, list):
                        for detail in audited:
                            if not isinstance(detail, dict):
                                continue
                            candidate = detail.get("candidate")
                            if not isinstance(candidate, dict):
                                continue
                            eligibility = str(candidate.get("eligibility") or "").lower()
                            add({
                                "accession": candidate.get("accession"),
                                "status": "candidate" if eligibility == "eligible" else "rejected",
                                "decision": "candidate" if eligibility == "eligible" else "rejected",
                                "reasons": candidate.get("exclusion_reasons") or [],
                                "context_match_score": candidate.get("context_match_score"),
                                "case_count": candidate.get("case_count"),
                                "control_count": candidate.get("control_count"),
                                "sample_count": candidate.get("sample_count"),
                                "processed_files": candidate.get("processed_files"),
                            })
                    trace = outputs.get("selection_trace")
                    if isinstance(trace, list):
                        for item in trace:
                            if not isinstance(item, dict):
                                continue
                            add({
                                "accession": item.get("accession"),
                                "status": selection_status(item),
                                "decision": item.get("decision"),
                                "reasons": item.get("reasons") or [],
                            })
        except OSError:
            pass

        report_path = run_dir / "report.json"
        try:
            if report_path.is_file():
                payload = json.loads(report_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    rows = payload.get("dataset_selection_trace") or payload.get("datasets")
                    if isinstance(rows, list):
                        for row in rows:
                            if not isinstance(row, dict):
                                continue
                            add({
                                "accession": row.get("accession"),
                                "status": selection_status(row),
                                "decision": row.get("decision"),
                                "reasons": row.get("reasons") or row.get("exclusion_reasons") or [],
                                "context_match_score": row.get("context_match_score"),
                                "candidate": row.get("candidate"),
                            })
        except (OSError, json.JSONDecodeError):
            pass
        return candidates

    @staticmethod
    def _record_trace(
        context: ModuleContext,
        child_run_id: str,
        descriptors: list[ToolDescriptor],
        event: TraceEvent,
    ) -> None:
        if context.activity_sink is None:
            return
        context.activity_sink(project_trace_event(
            project_id=context.project.project_id,
            work_item_id=context.item.item_id,
            child_run_id=child_run_id,
            event=event,
            descriptors=descriptors,
        ))


class IndependentReviewModule:
    descriptor = ModuleDescriptor(
        name="independent_review",
        description="Run deterministic integrity, provenance and schema-alignment gates over durable results.",
        input_types=("WorkItemResult[]", "ArtifactRecord[]"), output_types=("AssessmentRecord[]",),
        execution_policy="read_only_reviewer", side_effect_free=True, replay_safe=True,
    )

    def execute(self, context: ModuleContext) -> ModuleExecution:
        assessments: list[AssessmentRecord] = []
        failures: list[str] = []
        for item_id, result in context.prior_results.items():
            artifact_rows = [row for row in context.artifacts if row.work_item_id == item_id]
            for artifact in artifact_rows:
                path = context.artifact_path(artifact)
                actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                passed = actual == artifact.sha256
                if not passed:
                    failures.append(artifact.artifact_id)
                assessments.append(AssessmentRecord(
                    project_id=context.project.project_id, target_id=artifact.artifact_id,
                    target_digest=artifact.sha256, dimension=AssessmentDimension.INTEGRITY,
                    level=AssessmentLevel.A0,
                    result=AssessmentResult.PASS if passed else AssessmentResult.FAIL,
                    actor="independent_review", method="sha256_recalculation",
                    rationale="Artifact digest matches the immutable registry." if passed else "Artifact is missing or its digest changed.",
                    blocking=not passed,
                ))
            problematic = result.status in {WorkItemStatus.FAILED, WorkItemStatus.BLOCKED, WorkItemStatus.NEEDS_INPUT}
            assessments.append(AssessmentRecord(
                project_id=context.project.project_id, target_id=item_id,
                target_digest=work_item_result_digest(result),
                dimension=AssessmentDimension.METHODOLOGY, level=AssessmentLevel.A0,
                result=AssessmentResult.FAIL if problematic else AssessmentResult.PASS,
                actor="independent_review", method="typed_status_gate",
                rationale=f"Work item terminal status is {result.status.value}.", blocking=problematic,
            ))
        status = WorkItemStatus.COMPLETED_WITH_GAPS if failures else WorkItemStatus.COMPLETED
        output_path = context.output_dir / "review_summary.json"
        _write_json(output_path, {"assessment_count": len(assessments), "blocking_failures": failures})
        return ModuleExecution(
            result=_result(context.item, status, f"Completed {len(assessments)} independent A0 assessments.",
                           outputs={"assessment_count": len(assessments), "blocking_failures": failures},
                           limitations=[] if not failures else ["Blocking artifact-integrity failures must be resolved before release."]),
            artifacts=[PendingArtifact(output_path, "review_summary", "application/json")],
            assessments=assessments,
        )


class ResearchReportModule:
    descriptor = ModuleDescriptor(
        name="research_report",
        description="Render a project report only from structured work-item results and registered artifacts.",
        input_types=("WorkItemResult[]", "ArtifactRecord[]"), output_types=("ResearchReport",),
        execution_policy="deterministic_local", side_effect_free=True, replay_safe=True,
    )

    def execute(self, context: ModuleContext) -> ModuleExecution:
        lines = [f"# {context.project.title}", "", "## Research question", "",
                 context.project.goal.question, "", "## Workflow results", ""]
        gaps: list[str] = []
        for item_id, result in context.prior_results.items():
            lines.extend([f"### {item_id}", "", f"- Module: `{result.module}`",
                          f"- Status: `{result.status.value}`", f"- Summary: {result.summary}"])
            if result.evidence_refs:
                lines.append(f"- Evidence references: {', '.join(result.evidence_refs)}")
            if result.limitations:
                lines.append("- Limitations: " + "; ".join(result.limitations))
                gaps.extend(f"{item_id}: {value}" for value in result.limitations)
            lines.append("")
        target_result = next(
            (result for result in context.prior_results.values()
             if result.module == "target_discovery"),
            None,
        )
        if target_result is not None:
            lines.extend([
                "## Target-discovery deliverables", "",
                f"- Domain status: `{target_result.outputs.get('terminal_status', target_result.status.value)}`",
                f"- Ranked candidates: {target_result.outputs.get('ranked_target_count', 0)}",
                f"- TargetCards: {target_result.outputs.get('target_card_count', 0)}",
                f"- Falsifiable experiment plans: {target_result.outputs.get('experiment_plan_count', 0)}",
                f"- Required domain artifacts complete: `{target_result.outputs.get('deliverables_complete', False)}`",
                "- Scientific details remain in the registered target-discovery report, ranking and TargetCard artifacts.",
                "",
            ])
        lines.extend(["## Registered artifacts", ""])
        for artifact in context.artifacts:
            lines.append(f"- `{artifact.logical_name}` v{artifact.version}: `{artifact.uri}` (sha256 `{artifact.sha256}`)")
        lines.extend(["", "## Evidence gaps and next actions", ""])
        lines.extend([f"- {gap}" for gap in gaps] or ["- No workflow-reported gaps."])
        lines.extend(["", "## Interpretation boundary", "",
                      "This report records executed work and evidence gaps. It does not convert rankings, model outputs, or retrieval hits into biological truth.", ""])
        path = context.output_dir / "research_report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return ModuleExecution(
            result=_result(context.item, WorkItemStatus.COMPLETED if not gaps else WorkItemStatus.COMPLETED_WITH_GAPS,
                           "Generated a source-bounded project report from durable results.",
                           outputs={"reported_items": len(context.prior_results), "gap_count": len(gaps)}),
            artifacts=[PendingArtifact(path, "research_report", "text/markdown")],
        )


def default_research_registry(settings: Settings) -> ResearchModuleRegistry:
    return ResearchModuleRegistry([
        ProjectBriefModule(), LiteratureSearchModule(), HypothesisGenerationModule(StepClient.from_settings(settings)),
        TargetDiscoveryModule(), IndependentReviewModule(), ResearchReportModule(),
    ])


__all__ = [
    "IndependentReviewModule", "LiteratureSearchModule", "ModuleContext", "ModuleDescriptor",
    "ModuleExecution", "PendingArtifact", "ProjectBriefModule", "ResearchModuleRegistry",
    "ResearchReportModule", "TargetDiscoveryModule", "default_research_registry",
]
