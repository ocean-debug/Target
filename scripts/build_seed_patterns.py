"""Rebuild and verify the paper-strategy corpus (run in the configured remote workspace).

Reads paper_strategy/patterns.jsonl, validates every record against the
canonical schema (stale digests are recomputed), rewrites the file in
normalized order and refreshes MANIFEST.json with per-pattern SHA-256
checksums. Idempotent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from target_agent.paper_strategy import BestPracticePattern, StrategyPattern

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "paper_strategy" / "patterns.jsonl"
MANIFEST = ROOT / "paper_strategy" / "MANIFEST.json"


def main() -> dict:
    if not PATTERNS.is_file():
        raise SystemExit(f"missing corpus: {PATTERNS}")
    rows = []
    for line_number, line in enumerate(PATTERNS.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {line_number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"pattern record at line {line_number} is not an object")
        payload.pop("digest", None)
        try:
            record = StrategyPattern.model_validate(payload)
        except ValidationError:
            record = BestPracticePattern.model_validate(payload)
        record.digest = record.compute_digest()
        rows.append(record)
    rows.sort(key=lambda row: row.pattern_id)
    lines = [row.model_dump_json() for row in rows]
    PATTERNS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "contract_version": "0.1.0",
        "count": len(rows),
        "validation_levels": {
            level: sum(1 for row in rows if row.validation_level == level)
            for level in ("discovery_pattern", "best_practice")
        },
        "review_pending": sum(
            1 for row in rows
            if row.review.life_science_review != "approved" or row.review.engineering_review != "approved"
        ),
        "patterns": [
            {"pattern_id": row.pattern_id, "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest()}
            for row, line in zip(rows, lines)
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
