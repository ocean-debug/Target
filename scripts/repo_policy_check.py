from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".pytest_cache", "__pycache__", "runs", "cache", "artifacts", "models"}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".js", ".css", ".html", ".example", ".sh"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)(?:api[_-]?key|token|secret)\s*[:=]\s*[\"'][A-Za-z0-9_./+-]{24,}[\"']"),
    re.compile(r"(?im)^(?:STEP_API_KEY|NCBI_API_KEY)\s*=\s*[A-Za-z0-9_./+-]{24,}\s*$"),
    re.compile(r"-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----"),
]
LOCAL_ABSOLUTE = re.compile(r"(?:[A-Za-z]:\\Users\\|/Users/|/home/[^/\s]+/)")


def main() -> None:
    violations = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        relative = path.relative_to(ROOT)
        if relative.as_posix() == "scripts/repo_policy_check.py":
            continue
        if path.stat().st_size > 5 * 1024 * 1024:
            violations.append(f"large file: {relative}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".env.example":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            violations.append(f"possible secret: {relative}")
        if LOCAL_ABSOLUTE.search(text):
            violations.append(f"local absolute path: {relative}")
    if violations:
        raise SystemExit("\n".join(violations))
    print("REPO_POLICY=OK")


if __name__ == "__main__":
    main()
