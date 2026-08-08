"""Static validation of deployment assets (Docker / Compose / Singularity / runbook).

Run without Docker: verifies that the deployment files exist, are well-formed
and carry the required product contract (healthcheck, persistent volume,
secret-safe env handling, runnable entrypoint). This is a build-gate check,
not a substitute for an actual image build.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


dockerfile = ROOT / "Dockerfile"
if dockerfile.is_file():
    text = read(dockerfile)
    check("Dockerfile exists", True)
    for token in ("FROM python:3.11-slim", "ENTRYPOINT", "CMD", "HEALTHCHECK", "EXPOSE 8888", "VOLUME"):
        check(f"Dockerfile contains {token}", token in text)
else:
    check("Dockerfile exists", False, "missing Dockerfile")

check(".dockerignore exists", (ROOT / ".dockerignore").is_file())
if (ROOT / ".dockerignore").is_file():
    ign = read(ROOT / ".dockerignore")
    check(".dockerignore excludes .env and .git", ".env" in ign and ".git" in ign)

compose_path = ROOT / "docker-compose.yml"
if compose_path.is_file():
    try:
        compose = yaml.safe_load(read(compose_path)) or {}
        service = (compose.get("services") or {}).get("target-agent") or {}
        check("compose parses as YAML", True)
        check("compose has target-agent service", bool(service))
        check("compose has build context", isinstance(service.get("build"), dict) and service["build"].get("context") == ".")
        check("compose maps port 8888", any(str(port).endswith(":8888") for port in (service.get("ports") or [])))
        check("compose mounts target-data:/data", any(
            str(v).startswith("target-data:") and str(v).endswith(":/data")
            for v in (service.get("volumes") or [])
        ))
        check("compose has healthcheck", "healthcheck" in service)
        check("compose defines data volume", "target-data" in (compose.get("volumes") or {}))
    except yaml.YAMLError as exc:
        check("compose parses as YAML", False, str(exc))
else:
    check("compose parses as YAML", False, "missing docker-compose.yml")

sif = ROOT / "singularity" / "target.def"
if sif.is_file():
    text = read(sif)
    check("singularity def exists", True)
    for token in ("Bootstrap: docker", "From: python:3.11-slim", "%files", "%post", "%runscript"):
        check(f"singularity def contains {token}", token in text)
    for asset in ("src", "configs", "workflows", "skills", "paper_strategy"):
        check(f"singularity def copies {asset}", f"{asset} /opt/target/" in text)
else:
    check("singularity def exists", False, "missing singularity/target.def")

runbook = ROOT / "docs" / "DEPLOYMENT.md"
if runbook.is_file():
    text = read(runbook)
    check("deployment runbook exists", True)
    for token in ("docker compose up -d", "singularity build", "target-agent doctor", "/healthz"):
        check(f"runbook mentions {token}", token in text)
else:
    check("deployment runbook exists", False, "missing docs/DEPLOYMENT.md")

failed = [row for row in checks if not row[1]]
for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
print(f"DEPLOYMENT_ASSETS={len(checks) - len(failed)}/{len(checks)}")
sys.exit(1 if failed else 0)