"""Flask API and static single-page research workbench."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from pydantic import ValidationError

from .contracts import TaskSpec
from .runtime import TargetDiscoveryRuntime


def create_app(runtime: TargetDiscoveryRuntime | None = None) -> Flask:
    runtime = runtime or TargetDiscoveryRuntime()
    static_dir = Path(__file__).with_name("web") / "static"
    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")

    @app.get("/")
    def index():
        return send_from_directory(static_dir, "index.html")

    @app.post("/api/runs")
    def create_run():
        try:
            task = TaskSpec.model_validate(request.get_json(force=True))
        except ValidationError as exc:
            return jsonify({"error": "invalid TaskSpec", "detail": exc.errors(include_url=False)}), 400
        run_id = f"run-{task.task_id.replace('task-', '')}"

        def worker() -> None:
            try:
                runtime.run(task, run_id=run_id)
            except Exception as exc:  # status file is the user-visible failure boundary
                run_dir = runtime.runs_dir / run_id
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "status.json").write_text(json.dumps({
                    "contract_version": "2.0.0", "run_id": run_id, "task_id": task.task_id,
                    "state": "terminal", "terminal_status": "failed", "detail": {"error": exc.__class__.__name__},
                }), encoding="utf-8")

        threading.Thread(target=worker, name=run_id, daemon=True).start()
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
        return send_file(path, as_attachment=name.endswith((".md", ".json", ".jsonl")))

    return app


def _safe_run_dir(root: Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id or not run_id.startswith("run-"):
        raise ValueError("invalid run id")
    root = root.resolve()
    candidate = (root / run_id).resolve()
    if root not in candidate.parents:
        raise ValueError("run path escaped root")
    return candidate

