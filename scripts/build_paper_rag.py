"""Fetch, append and verify the paper-abstract RAG store (remote workspace).

Reads paper_strategy/corpus/corpus.jsonl (optionally restricted to gold
records), fetches bounded abstracts through Europe PMC, chunks them with
per-chunk digests, and writes paper_strategy/rag/chunks.jsonl plus
MANIFEST.json. Idempotent: existing chunk ids are never rewritten.

Only abstracts are persisted; methods/full text stays in memory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from target_agent.paper_corpus import CorpusStore
from target_agent.paper_rag import PaperRagStore, build_chunks
from target_agent.pattern_extraction import CurationStore, EuropePmcMetaFetcher

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "paper_strategy" / "corpus" / "corpus.jsonl"
CURATION = ROOT / "paper_strategy" / "corpus" / "curation.jsonl"
RAG_STORE = ROOT / "paper_strategy" / "rag" / "chunks.jsonl"


def main() -> dict:
    fetcher = EuropePmcMetaFetcher()
    store = PaperRagStore(RAG_STORE)
    all_papers = CorpusStore(CORPUS).all()
    only_gold = os.environ.get("PAPER_RAG_ONLY_GOLD", "0") == "1"
    if only_gold:
        gold = set(CurationStore(CURATION).gold_pmids())
        papers = [row for row in all_papers if row.pmid in gold]
    else:
        papers = [row for row in all_papers if row.status == "candidate"]
    pmids_env = os.environ.get("PAPER_RAG_PMIDS", "")
    if pmids_env.strip():
        wanted = {value.strip() for value in pmids_env.split(",") if value.strip()}
        papers = [row for row in papers if row.pmid in wanted]
    limit = int(os.environ.get("PAPER_RAG_LIMIT", "0"))
    if limit > 0:
        papers = papers[:limit]
    existing = {chunk.pmid for chunk in store.all()}
    added_chunks = 0
    skipped_chunks = 0
    failed: list[dict[str, str]] = []
    for row in papers:
        if row.pmid in existing:
            skipped_chunks += 1
            continue
        try:
            meta = fetcher.fetch(row.pmid)
            if meta is None:
                failed.append({"pmid": row.pmid, "error": "no Europe PMC record"})
                continue
            chunks = build_chunks(meta, context_tags=row.query_buckets)
            result = store.add_many(chunks)
            added_chunks += result["added"]
            skipped_chunks += result["skipped"]
        except Exception as exc:
            failed.append({"pmid": row.pmid, "error": str(exc)[:200]})
    manifest = store.write_manifest()
    return {
        "added_chunks": added_chunks,
        "skipped_chunks": skipped_chunks,
        "failed_papers": failed,
        "manifest_count": manifest["chunks"],
        "card": store.corpus_card(),
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
