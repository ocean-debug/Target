"""Command-line entry points for runs, diagnostics, schemas and the workbench."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import yaml

from .alignment import generate
from .contracts import TaskContext, TaskSpec
from .legacy import adapt_task_spec_2_0
from .llm import StepClient
from .planner import Planner
from .research_contracts import DecisionAction, DecisionEvent, ResearchProjectSpec
from .research_runtime import ResearchProjectRuntime
from .research_store import ResearchProjectStore
from .runtime import TargetDiscoveryRuntime
from .runtime_langgraph import LangGraphRuntime
from .schema_export import export_schemas
from .settings import Settings, load_settings
from .tools import default_registry
from .webapp import create_app


def load_task(path: Path) -> TaskSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload.get("contract_version") == "2.0.0":
        return adapt_task_spec_2_0(payload)
    return TaskSpec.model_validate(payload)


def load_research_project(path: Path) -> ResearchProjectSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ResearchProjectSpec.model_validate(payload)


def _doctor(settings: Settings) -> dict:
    required = ["flask", "pydantic", "pydantic_settings", "requests", "waitress", "yaml"]
    optional = ["pydeseq2", "gseapy", "scanpy", "anndata", "cellxgene_census"]
    registry = default_registry(settings)
    rscript = shutil.which("Rscript")
    limma_package = False
    if rscript:
        check = subprocess.run(
            [rscript, "-e", "quit(status=ifelse(requireNamespace('limma', quietly=TRUE),0,1))"],
            capture_output=True, text=True, timeout=20, check=False,
        )
        limma_package = check.returncode == 0
    return {
        "settings": settings.public_summary(),
        "required_dependencies": {name: bool(importlib.util.find_spec(name)) for name in required},
        "optional_dependencies": {name: bool(importlib.util.find_spec(name)) for name in optional},
        "limma_backend": {
            "enabled": settings.enable_limma,
            "rscript_available": bool(rscript),
            "limma_package_available": limma_package,
            "ready": settings.enable_limma and bool(rscript) and limma_package,
        },
        "enabled_tools": registry.names,
        "registry_contract_valid": True,
    }


def _smoke_test(settings: Settings) -> dict:
    client = StepClient.from_settings(settings)
    if not client:
        raise SystemExit("Step API is not configured; provide it through an untracked env file or process environment")
    registry = default_registry(settings)
    planner = Planner(client, registry)
    task = TaskSpec(
        task_type="disease_to_target",
        question="Plan a traceable Alzheimer disease target-discovery workflow",
        context=TaskContext(disease="Alzheimer disease", tissue="brain"),
    )
    plan = planner.create_plan(task)
    if plan.fallback_used or not plan.planner_backend.startswith("step:"):
        raise SystemExit(f"Step structured-plan validation failed; backend={plan.planner_backend}")
    return {
        "configured": True, "schema_valid": True, "planner_backend": plan.planner_backend,
        "step_count": len(plan.steps), "provider_request": client.last_request_meta,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="target-agent")
    parser.add_argument("--env-file", type=Path, help="Select a dotenv file; process environment remains authoritative")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run or resume an Agent case")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--run-id")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--runs-dir", type=Path)
    run.add_argument("--cache-dir", type=Path)
    run.add_argument("--runtime", choices=["legacy", "langgraph"], default="langgraph",
                     help="Execution engine; both are parity-tested and write identical artifacts")

    project_run = sub.add_parser("project-run", help="Run or resume a durable disease-target research project")
    project_run.add_argument("--input", type=Path, required=True)
    project_run.add_argument("--resume", action="store_true")
    project_run.add_argument("--projects-dir", type=Path)
    project_run.add_argument("--cache-dir", type=Path)

    project_status = sub.add_parser("project-status", help="Read durable project state without executing work")
    project_status.add_argument("--project-id", required=True)
    project_status.add_argument("--projects-dir", type=Path)

    project_approve = sub.add_parser("project-approve", help="Accept a frozen plan, supervised work item, or release gate")
    project_approve.add_argument("--project-id", required=True)
    project_approve.add_argument("--target-id", required=True,
                                 help="Plan id, work-item id, or release:<plan-id>")
    project_approve.add_argument("--actor", required=True)
    project_approve.add_argument("--rationale", required=True)
    project_approve.add_argument("--projects-dir", type=Path)
    project_approve.add_argument("--resume", action="store_true",
                                 help="Resume the project immediately after recording acceptance")

    schemas = sub.add_parser("export-schemas", help="Export canonical Pydantic JSON Schemas")
    schemas.add_argument("--output", type=Path, default=Path("schemas"))

    alignment = sub.add_parser("generate-alignment", help="Generate review-gated alignment cases")
    alignment.add_argument("--output", type=Path, default=Path("alignment_data"))

    sub.add_parser("doctor", help="Check configuration and capabilities without printing secrets")
    sub.add_parser("llm-smoke-test", help="Make one real Step structured-planning request")

    diseases_cmd = sub.add_parser("diseases", help="List the OLS-verified disease library")
    diseases_cmd.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    run_disease = sub.add_parser("run-disease", help="Run one or more library diseases by id/name/synonym")
    run_disease.add_argument("--disease", required=True,
                             help="Comma-separated disease ids, names or synonyms (e.g. uc,ra,ad)")
    run_disease.add_argument("--kind", choices=["normal", "missing_context", "conflicting_evidence", "trap"],
                             default="normal", help="Task template bucket from the disease library")
    run_disease.add_argument("--run-id", default="run-disease", help="Run-id prefix; each run is '<prefix>-<disease id>'")
    run_disease.add_argument("--runs-dir", type=Path)
    run_disease.add_argument("--cache-dir", type=Path)
    run_disease.add_argument("--runtime", choices=["legacy", "langgraph"], default="langgraph")
    run_disease.add_argument("--summary-out", type=Path, help="Optional JSON summary of the batch")

    serve = sub.add_parser("serve", help="Start the single-page research workbench with Waitress")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, required=True, help="Bind port supplied by the external deployment profile")
    serve.add_argument("--runs-dir", type=Path)
    serve.add_argument("--projects-dir", type=Path)
    serve.add_argument("--cache-dir", type=Path)
    serve.add_argument("--runtime", choices=["legacy", "langgraph"], default="langgraph")
    serve.add_argument("--dev", action="store_true", help="Use Flask's development server")

    args = parser.parse_args()
    settings = load_settings(args.env_file)
    if args.command == "run":
        runtime_cls = LangGraphRuntime if args.runtime == "langgraph" else TargetDiscoveryRuntime
        runtime = runtime_cls(runs_dir=args.runs_dir, cache_dir=args.cache_dir, settings=settings)
        print(json.dumps(runtime.run(load_task(args.input), run_id=args.run_id, resume=args.resume), indent=2, ensure_ascii=False))
    elif args.command == "project-run":
        project_runtime = ResearchProjectRuntime(
            projects_dir=args.projects_dir, cache_dir=args.cache_dir, settings=settings,
        )
        print(json.dumps(project_runtime.run(load_research_project(args.input), resume=args.resume),
                         indent=2, ensure_ascii=False))
    elif args.command == "project-status":
        store = ResearchProjectStore(args.projects_dir or settings.projects_dir, args.project_id)
        spec = store.load_spec()
        state = store.load_state()
        if spec is None:
            raise SystemExit(f"project not found: {args.project_id}")
        print(json.dumps({
            "spec": spec.model_dump(mode="json"),
            "state": state.model_dump(mode="json") if state else None,
            "work_item_results": [row.model_dump(mode="json") for row in store.load_work_item_results().values()],
            "artifacts": [row.model_dump(mode="json") for row in store.read_artifacts()],
            "decisions": [row.model_dump(mode="json") for row in store.read_decisions()],
        }, indent=2, ensure_ascii=False))
    elif args.command == "project-approve":
        store = ResearchProjectStore(args.projects_dir or settings.projects_dir, args.project_id)
        spec, plan = store.load_spec(), store.load_plan()
        if spec is None or plan is None:
            raise SystemExit(f"project or plan not found: {args.project_id}")
        allowed = {plan.plan_id, *(item.item_id for item in plan.items), f"release:{plan.plan_id}"}
        if args.target_id not in allowed:
            raise SystemExit("target id is not part of the frozen plan")
        decision = next((row for row in store.read_decisions()
                         if row.action == DecisionAction.ACCEPT and args.target_id in row.target_ids), None)
        if decision is None:
            decision = DecisionEvent(
                project_id=args.project_id, action=DecisionAction.ACCEPT,
                target_ids=[args.target_id], actor=args.actor, rationale=args.rationale,
                reversible=False,
            )
            store.append_decision(decision)
        result = {"decision": decision.model_dump(mode="json")}
        if args.resume:
            result["state"] = ResearchProjectRuntime(
                projects_dir=args.projects_dir, settings=settings,
            ).run(spec, resume=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "export-schemas":
        for path in export_schemas(args.output):
            print(path)
    elif args.command == "generate-alignment":
        print(json.dumps(generate(args.output), ensure_ascii=False))
    elif args.command == "doctor":
        print(json.dumps(_doctor(settings), indent=2, ensure_ascii=False))
    elif args.command == "llm-smoke-test":
        print(json.dumps(_smoke_test(settings), indent=2, ensure_ascii=False))
    elif args.command == "diseases":
        from .diseases import load_library

        library = load_library()
        rows = [
            {
                "id": entry.id, "name": entry.name, "name_zh": entry.name_zh,
                "ontology_id": entry.ontology_id, "category": entry.category,
                "reference_targets": len(entry.reference_targets),
                "tissue": entry.context.tissue, "cell_type": entry.context.cell_type,
            }
            for entry in library.diseases
        ]
        if args.json:
            print(json.dumps({"version": library.version, "diseases": rows}, indent=2, ensure_ascii=False))
        else:
            print(f"disease library v{library.version} — {len(rows)} entries (ontology ids OLS-verified)")
            print(f"{'id':<10} {'ontology':<16} {'category':<12} {'refs':>4}  name (zh)")
            for row in rows:
                print(f"{row['id']:<10} {row['ontology_id']:<16} {row['category']:<12} "
                      f"{row['reference_targets']:>4}  {row['name']} ({row['name_zh']})")
    elif args.command == "run-disease":
        from .diseases import load_library

        library = load_library()
        runtime_cls = LangGraphRuntime if args.runtime == "langgraph" else TargetDiscoveryRuntime
        runtime = runtime_cls(runs_dir=args.runs_dir, cache_dir=args.cache_dir, settings=settings)
        queries = [item.strip() for item in args.disease.split(",") if item.strip()]
        if not queries:
            raise SystemExit("--disease requires at least one id, name or synonym")
        summary_rows = []
        for query in queries:
            entry = library.find(query)
            task = library.to_task_spec(query, kind=args.kind)
            run_id = f"{args.run_id}-{entry.id}"
            print(f"[run-disease] {entry.id}: {task.question} (kind={args.kind}, run_id={run_id})")
            result = runtime.run(task, run_id=run_id)
            ranked_path = runtime.runs_dir / run_id / "ranked_targets.json"
            top_genes: list[str] = []
            if ranked_path.exists():
                ranked = json.loads(ranked_path.read_text(encoding="utf-8"))
                top_genes = [row.get("gene", "?") for row in ranked[:3]]
            summary_rows.append({
                "disease_id": entry.id, "disease": entry.name, "kind": args.kind,
                "run_id": run_id, "terminal_status": result.get("terminal_status"),
                "highlighted_targets": top_genes,
                "tool_calls": result.get("detail", {}).get("tool_calls"),
            })
        print(f"\n{'disease':<10} {'terminal_status':<22} top-3 targets")
        for row in summary_rows:
            print(f"{row['disease_id']:<10} {str(row['terminal_status']):<22} {', '.join(row['highlighted_targets'])}")
        if args.summary_out:
            args.summary_out.parent.mkdir(parents=True, exist_ok=True)
            args.summary_out.write_text(json.dumps(
                {"library_version": library.version, "kind": args.kind, "runs": summary_rows},
                indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"summary written to {args.summary_out}")
    elif args.command == "serve":
        runtime_cls = LangGraphRuntime if args.runtime == "langgraph" else TargetDiscoveryRuntime
        runtime = runtime_cls(runs_dir=args.runs_dir, cache_dir=args.cache_dir, settings=settings)
        research_runtime = ResearchProjectRuntime(
            projects_dir=args.projects_dir, cache_dir=args.cache_dir, settings=settings,
        )
        app = create_app(runtime, research_runtime)
        if args.dev:
            app.run(host=args.host, port=args.port, threaded=True)
        else:
            from waitress import serve as waitress_serve
            waitress_serve(app, host=args.host, port=args.port, threads=settings.web_workers)


__all__ = ["main", "load_task", "load_research_project", "_doctor", "_smoke_test"]
