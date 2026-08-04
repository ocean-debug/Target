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

    @app.post("/api/runs")
    def create_run():
        try:
            task = TaskSpec.model_validate(request.get_json(force=True))
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

        return Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

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
