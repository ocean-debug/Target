"""Fetch, append and verify the PubMed candidate corpus (run on the remote workspace).

Reads/writes paper_strategy/corpus/corpus.jsonl through the same E-utilities
pipeline exposed by the CLI (target-agent pattern corpus refresh), then writes
MANIFEST.json with per-record SHA-256 checksums. Idempotent: existing PMIDs
are never rewritten.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from target_agent.paper_corpus import CorpusStore, RequestsEutilsClient, fetch_candidates

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "paper_strategy" / "corpus" / "corpus.jsonl"


def main() -> dict:
    client = RequestsEutilsClient(
        email=os.environ.get("NCBI_EMAIL") or None,
        api_key=os.environ.get("NCBI_API_KEY") or None,
    )
    records = fetch_candidates(
        client,
        year_min=int(os.environ.get("CORPUS_YEAR_MIN", "2021")),
        year_max=int(os.environ.get("CORPUS_YEAR_MAX", "2026")),
        retmax_per_query=int(os.environ.get("CORPUS_RETMAX", "8")),
        max_candidates=int(os.environ.get("CORPUS_MAX_CANDIDATES", "200")),
    )
    store = CorpusStore(CORPUS)
    result = store.add_many(records)
    manifest = store.write_manifest()
    return {**result, "manifest_count": manifest["count"], "card": store.corpus_card()}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
