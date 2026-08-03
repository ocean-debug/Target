"""Command-line entry points for runs, schemas, alignment data and the workbench."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .alignment import generate
from .contracts import TaskSpec
from .runtime import TargetDiscoveryRuntime
from .schema_export import export_schemas
from .webapp import create_app


def load_task(path: Path) -> TaskSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TaskSpec.model_validate(payload)


def main() -> None:
    parser = argparse.ArgumentParser(prog="target-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run or resume an Agent case")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--run-id")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--runs-dir", type=Path)
    run.add_argument("--cache-dir", type=Path)

    schemas = sub.add_parser("export-schemas", help="Export canonical Pydantic JSON Schemas")
    schemas.add_argument("--output", type=Path, default=Path("schemas"))

    alignment = sub.add_parser("generate-alignment", help="Generate review-gated alignment cases")
    alignment.add_argument("--output", type=Path, default=Path("alignment_data"))

    serve = sub.add_parser("serve", help="Start the single-page research workbench")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--runs-dir", type=Path)
    serve.add_argument("--cache-dir", type=Path)

    args = parser.parse_args()
    if args.command == "run":
        runtime = TargetDiscoveryRuntime(runs_dir=args.runs_dir, cache_dir=args.cache_dir)
        print(json.dumps(runtime.run(load_task(args.input), run_id=args.run_id, resume=args.resume), indent=2, ensure_ascii=False))
    elif args.command == "export-schemas":
        for path in export_schemas(args.output):
            print(path)
    elif args.command == "generate-alignment":
        print(json.dumps(generate(args.output), ensure_ascii=False))
    elif args.command == "serve":
        runtime = TargetDiscoveryRuntime(runs_dir=args.runs_dir, cache_dir=args.cache_dir)
        create_app(runtime).run(host=args.host, port=args.port, threaded=True)

