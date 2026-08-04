"""Flask API and static single-page research workbench."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from pydantic import ValidationError

from .contracts import CONTRACT_VERSION, TaskSpec, new_id
from .runtime import TargetDiscoveryRuntime


DEMO_CASES = (
    {
        "id": "luad", "run_id": "run-luad-v21-cached-3", "kind": "main",
        "title": "肺腺癌靶点发现", "subtitle": "完整证据链与TargetCard",
        "description": "动态GEO筛选、组学分析、遗传学/文献/药物融合与实验设计。",
    },
    {
        "id": "uc", "run_id": "run-uc-v21-cached-3", "kind": "boundary",
        "title": "UC可靠降级", "subtitle": "证据不足时不伪造结论",
        "description": "展示not_covered、context_mismatch和completed_with_gaps。",
    },
    {
        "id": "ad", "run_id": "run-ad-v21-cached-3", "kind": "generalization",
        "title": "阿尔茨海默病", "subtitle": "跨疾病冷启动案例",
        "description": "展示通用疾病标准化与公开数据发现能力。",
    },
)


class BoundedExecutor:
    def __init__(self, workers: int, queue_size: int):
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="target-agent")
        self.capacity = threading.BoundedSemaphore(workers + queue_size)
        self.workers = workers
        self.queue_size = queue_size

    def submit(self, function, *args) -> bool:
        if not self.capacity.acquire(blocking=False):
            return False
        future = self.executor.submit(function, *args)
        future.add_done_callback(lambda _: self.capacity.release())
        return True


def create_app(runtime: TargetDiscoveryRuntime | None = None) -> Flask:
    if runtime is None:
        from .runtime_langgraph import LangGraphRuntime
        runtime = LangGraphRuntime()
    static_dir = Path(__file__).with_name("web") / "static"
    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")
    pool = BoundedExecutor(runtime.settings.web_workers, runtime.settings.web_queue_size)

    @app.errorhandler(ValueError)
    def invalid_path(exc):
        return jsonify({"error": "invalid request path", "detail": str(exc)}), 400

    @app.get("/")
    def index():
        return send_from_directory(static_dir, "index.html")

    @app.get("/healthz")
    def health():
        public = runtime.settings.public_summary()
        return jsonify({
            "status": "ok", "contract_version": CONTRACT_VERSION,
            "service": {"status": "ok"},
            "database": {
                "kind": "filesystem_evidence_store",
                "status": "ok" if public["runs_dir_writable"] else "unavailable",
            },
            "cache": {"status": "ok" if public["cache_dir_writable"] else "unavailable"},
            "executor": {"status": "ok", "workers": pool.workers, "queue_size": pool.queue_size},
        })

    @app.get("/api/capabilities")
    def capabilities():
        import importlib.util

        return jsonify({
            "contract_version": CONTRACT_VERSION,
            "settings": runtime.settings.public_summary(),
            "tools": runtime.registry.public_capabilities(),
            "analysis_backends": {
                "pydeseq2": bool(importlib.util.find_spec("pydeseq2")),
                "gseapy": bool(importlib.util.find_spec("gseapy")),
                "scanpy_pseudobulk": bool(importlib.util.find_spec("scanpy")),
                "cellxgene_census": bool(importlib.util.find_spec("cellxgene_census")),
                "limma_declared": runtime.settings.enable_limma,
            },
            "limits": {
                "max_tool_calls": 30, "max_review_rounds": 2,
                "max_geo_candidates": 10, "max_datasets_to_analyze": 2,
                "max_cells": 100_000, "max_download_mb": 2048,
            },
        })

    @app.get("/api/diseases")
    def diseases():
        try:
            from .diseases import load_library

            library = load_library()
        except Exception as exc:
            return jsonify({"error": "disease library unavailable", "detail": exc.__class__.__name__}), 503
        return jsonify({
            "version": library.version,
            "template_kinds": sorted(library.task_templates),
            "diseases": [
                {
                    "id": entry.id, "name": entry.name, "name_zh": entry.name_zh,
                    "ontology_id": entry.ontology_id, "category": entry.category,
                    "reference_target_count": len(entry.reference_targets),
                    "tissue": entry.context.tissue, "cell_type": entry.context.cell_type,
                }
                for entry in library.diseases
            ],
        })

    @app.get("/api/demo/cases")
    def demo_cases():
        cases = []
        for configured in DEMO_CASES:
            item = {key: value for key, value in configured.items() if key != "run_id"}
            run_dir = _safe_run_dir(runtime.runs_dir, configured["run_id"])
            status = _read_json(run_dir / "status.json")
            available = bool(status and (run_dir / "report.json").is_file())
            item["available"] = available
            item["recommended"] = configured["id"] == "luad"
            if available:
                item["run_id"] = configured["run_id"]
                item["terminal_status"] = status.get("terminal_status")
            cases.append(item)
        return jsonify({"contract_version": CONTRACT_VERSION, "cases": cases})

    @app.post("/api/runs")
    def create_run():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "request body must be a JSON object"}), 400
        try:
            task = TaskSpec.model_validate(payload)
        except ValidationError as exc:
            return jsonify({"error": "invalid TaskSpec", "detail": exc.errors(include_url=False)}), 400
        run_id = new_id("run")

        def worker() -> None:
            try:
                runtime.run(task, run_id=run_id)
            except Exception as exc:
                run_dir = runtime.runs_dir / run_id
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "status.json").write_text(json.dumps({
                    "contract_version": CONTRACT_VERSION, "run_id": run_id, "task_id": task.task_id,
                    "state": "terminal", "terminal_status": "failed", "detail": {"error": exc.__class__.__name__},
                }), encoding="utf-8")

        if not pool.submit(worker):
            return jsonify({"error": "run queue is full", "retryable": True}), 429
        return jsonify({"run_id": run_id, "status_url": f"/api/runs/{run_id}"}), 202

    @app.get("/api/runs/<run_id>")
    def get_run(run_id: str):
        path = _safe_run_dir(runtime.runs_dir, run_id) / "status.json"
        if not path.exists():
            return jsonify({"error": "run not found"}), 404
        return send_file(path, mimetype="application/json")

    @app.get("/api/runs/<run_id>/events")
    def events(run_id: str):
        run_dir = _safe_run_dir(runtime.runs_dir, run_id)
        if not run_dir.is_dir():
            return jsonify({"error": "run not found"}), 404

        def stream():
            delivered = 0
            idle = 0
            while idle < 600:
                trace_path = run_dir / "trace.jsonl"
                lines = trace_path.read_text(encoding="utf-8").splitlines() if trace_path.exists() else []
                for line in lines[delivered:]:
                    yield f"data: {line}\n\n"
                if len(lines) > delivered:
                    delivered = len(lines)
                    idle = 0
                else:
                    idle += 1
                status_path = run_dir / "status.json"
                if status_path.exists():
                    status = json.loads(status_path.read_text(encoding="utf-8"))
                    if status.get("terminal_status"):
                        yield f"event: terminal\ndata: {json.dumps(status, ensure_ascii=False)}\n\n"
                        break
                yield ": heartbeat\n\n"
                time.sleep(1)

        return Response(stream(), mimetype="text/event-stream", headers={
            "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
        })

    @app.get("/api/runs/<run_id>/bundle")
    def bundle(run_id: str):
        run_dir = _safe_run_dir(runtime.runs_dir, run_id)
        if not run_dir.is_dir():
            return jsonify({"error": "run not found"}), 404
        report_payload = _read_json(run_dir / "report.json")
        status_payload = _read_json(run_dir / "status.json")
        plan_payload = _read_json(run_dir / "execution_plan.json")
        if not report_payload or not status_payload or not plan_payload:
            return jsonify({"error": "run bundle is not ready"}), 409
        return jsonify(_build_public_bundle(
            run_id, status_payload, report_payload, plan_payload,
            _read_json(run_dir / "target_cards.json") or [],
            _read_jsonl(run_dir / "tool_results.jsonl"),
            _read_jsonl(run_dir / "evidence_items.jsonl"),
            _read_jsonl(run_dir / "trace.jsonl"),
        ))

    @app.get("/api/runs/<run_id>/report")
    def report(run_id: str):
        path = _safe_run_dir(runtime.runs_dir, run_id) / "report.md"
        if not path.exists():
            return jsonify({"error": "report not ready"}), 404
        return send_file(path, mimetype="text/markdown; charset=utf-8", as_attachment=True, download_name=f"{run_id}-report.md")

    @app.get("/api/runs/<run_id>/artifacts/<name>")
    def artifact(run_id: str, name: str):
        if Path(name).name != name:
            return jsonify({"error": "invalid artifact name"}), 400
        path = _safe_run_dir(runtime.runs_dir, run_id) / name
        if not path.is_file():
            return jsonify({"error": "artifact not found"}), 404
        return send_file(path, as_attachment=name.endswith((".md", ".json", ".jsonl", ".csv")))

    return app


def _safe_run_dir(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id or not run_id.startswith("run-"):
        raise ValueError("invalid run id")
    root = root.resolve()
    candidate = (root / run_id).resolve()
    if root not in candidate.parents:
        raise ValueError("run path escaped root")
    return candidate


def _read_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def _public_value(value):
    blocked_keys = {"tool_run_id", "event_id", "job_id", "run_dir", "cache_dir", "absolute_path"}
    if isinstance(value, dict):
        return {key: _public_value(item) for key, item in value.items() if key not in blocked_keys}
    if isinstance(value, list):
        return [_public_value(item) for item in value]
    if isinstance(value, str):
        if value.startswith("/") or (len(value) > 2 and value[1] == ":" and value[2] in "\\/"):
            return "[server artifact]"
    return value


def _build_public_bundle(
    run_id: str, status: dict, report: dict, plan: dict,
    cards: list[dict], tools: list[dict], evidence: list[dict], trace: list[dict],
) -> dict:
    claim_classes: dict[str, int] = {}
    genes: dict[str, int] = {}
    for item in evidence:
        claim_class = item.get("claim_class", "UNKNOWN")
        claim_classes[claim_class] = claim_classes.get(claim_class, 0) + 1
        gene = item.get("gene_symbol")
        if gene:
            genes[gene] = genes.get(gene, 0) + 1
    highlighted = set(report.get("highlighted_targets", []))
    selected_evidence = [item for item in evidence if item.get("gene_symbol") in highlighted][:24]
    if not selected_evidence:
        selected_evidence = evidence[:24]

    return _public_value({
        "contract_version": CONTRACT_VERSION,
        "run": {
            "run_id": run_id,
            "terminal_status": status.get("terminal_status"),
            "state": status.get("state"),
            "detail": status.get("detail", {}),
        },
        "question": report.get("question"),
        "context": report.get("context", {}),
        "plan": {
            "planner_backend": plan.get("planner_backend"),
            "fallback_used": plan.get("fallback_used", False),
            "steps": [
                {
                    "step_id": step.get("step_id"), "name": step.get("name"),
                    "tool": step.get("tool"), "dependencies": step.get("dependencies", []),
                    "success_criteria": step.get("success_criteria", []),
                    "degradation_conditions": step.get("degradation_conditions", []),
                }
                for step in plan.get("steps", [])
            ],
        },
        "dataset_selection_trace": report.get("dataset_selection_trace", []),
        "ranking": report.get("ranked_targets", []),
        "highlighted_targets": report.get("highlighted_targets", []),
        "target_cards": cards,
        "reviewer_findings": report.get("reviewer_findings", []),
        "report_policy": report.get("report_policy", {}),
        "tools": [
            {
                "tool_name": item.get("tool_name"), "status": item.get("status"),
                "coverage_status": item.get("coverage_status"),
                "context_match_score": item.get("context_match_score"),
                "cached": bool(item.get("cached")), "elapsed_ms": item.get("elapsed_ms"),
                "warnings": item.get("warnings", []), "limitations": item.get("limitations", []),
            }
            for item in tools
        ],
        "evidence": {
            "total": len(evidence), "claim_classes": claim_classes,
            "genes": dict(sorted(genes.items(), key=lambda pair: (-pair[1], pair[0]))[:20]),
            "items": [
                {
                    "gene_symbol": item.get("gene_symbol"), "claim_class": item.get("claim_class"),
                    "statement": item.get("statement"), "source": item.get("source", {}),
                    "source_span": item.get("source_span"), "context": item.get("context", {}),
                    "stance": item.get("stance"), "uncertainty": item.get("uncertainty"),
                    "context_match_score": item.get("context_match_score"),
                }
                for item in selected_evidence
            ],
        },
        "trace": [
            {
                "event_type": item.get("event_type"), "state": item.get("state"),
                "detail": item.get("detail", {}), "created_at": item.get("created_at"),
            }
            for item in trace
        ],
    })
