"""Europe PMC retrieval, stable chunking, FTS5 recall and span-checked extraction."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

import requests

from ..contracts import (
    ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, SourceLocator,
    Stance, ToolCapability, ToolResult, ToolStatus, new_id,
)
from ..llm import LLMUnavailable, StepClient
from .base import ScientificTool, ToolContext, ToolExecution


EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def stable_chunks(source_id: str, text: str, size: int = 1200, overlap: int = 150) -> list[dict[str, Any]]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        body = cleaned[start:end]
        digest = hashlib.sha256(f"{source_id}:{start}:{body}".encode()).hexdigest()[:16]
        chunks.append({"chunk_id": f"epmc-{source_id}-{digest}", "source_id": source_id, "start": start, "end": end, "text": body})
        if end == len(cleaned):
            break
        start = end - overlap
    return chunks


class EuropePMCRAGTool(ScientificTool):
    name = "europe_pmc_rag"
    version = "2.0.0"

    def __init__(self, session: requests.Session | None = None, llm: StepClient | None = None):
        self.session = session or requests.Session()
        self.llm = llm if llm is not None else StepClient.from_env()

    def _fetch(self, query: str, cache_path: Path) -> tuple[dict[str, Any], bool]:
        if os.getenv("TARGET_AGENT_CACHE_ONLY") == "1":
            if not cache_path.exists():
                raise FileNotFoundError("Europe PMC cache is missing in cache-only mode")
            return json.loads(cache_path.read_text(encoding="utf-8")), True
        try:
            response = self.session.get(
                EUROPE_PMC_SEARCH,
                params={"query": query, "format": "json", "pageSize": 25, "resultType": "core"},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return payload, False
        except (requests.RequestException, ValueError):
            if cache_path.exists():
                return json.loads(cache_path.read_text(encoding="utf-8")), True
            raise

    @staticmethod
    def _build_index(db_path: Path, chunks: list[dict[str, Any]]) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(chunk_id UNINDEXED, source_id UNINDEXED, text)")
            conn.execute("DELETE FROM chunks")
            conn.executemany("INSERT INTO chunks(chunk_id, source_id, text) VALUES (:chunk_id, :source_id, :text)", chunks)

    @staticmethod
    def _recall(db_path: Path, genes: list[str], limit: int = 30) -> list[dict[str, str]]:
        if not genes:
            return []
        query = " OR ".join(f'"{gene}"' for gene in genes)
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT chunk_id, source_id, text FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?",
                (query, limit),
            ).fetchall()
        return [{"chunk_id": row[0], "source_id": row[1], "text": row[2]} for row in rows]

    def _llm_extract(self, disease: str, genes: list[str], chunks: list[dict[str, str]]) -> list[dict[str, str]]:
        if not self.llm or not chunks:
            return []
        compact = [{"chunk_id": c["chunk_id"], "text": c["text"]} for c in chunks[:12]]
        system = (
            "Extract only explicit disease-gene claims from supplied chunks. Return JSON with key claims. "
            "Each claim must have gene, chunk_id, exact_quote copied verbatim, stance "
            "(supports/refutes/mixed/uncertain), and statement. Do not use outside knowledge."
        )
        try:
            payload = self.llm.json_completion(system, json.dumps({"disease": disease, "genes": genes, "chunks": compact}))
        except LLMUnavailable:
            return []
        by_id = {c["chunk_id"]: c["text"] for c in chunks}
        valid = []
        for claim in payload.get("claims", []):
            quote = str(claim.get("exact_quote", ""))
            chunk_id = str(claim.get("chunk_id", ""))
            gene = str(claim.get("gene", ""))
            if gene in genes and chunk_id in by_id and quote and quote in by_id[chunk_id]:
                valid.append(claim)
        return valid

    @staticmethod
    def _deterministic_extract(disease: str, genes: list[str], chunks: list[dict[str, str]]) -> list[dict[str, str]]:
        disease_terms = [term.lower() for term in {disease, "ulcerative colitis", "colitis", "inflammatory bowel"} if term]
        claims = []
        for chunk in chunks:
            for sentence in re.split(r"(?<=[.!?])\s+", chunk["text"]):
                lower = sentence.lower()
                gene = next((g for g in genes if re.search(rf"\b{re.escape(g)}\b", sentence, re.I)), None)
                if gene and any(term in lower for term in disease_terms) and len(sentence) >= 35:
                    claims.append({
                        "gene": gene, "chunk_id": chunk["chunk_id"], "exact_quote": sentence,
                        "stance": "uncertain", "statement": f"The source explicitly co-mentions {gene} and {disease}; direction requires scientific review.",
                    })
        unique = {}
        for claim in claims:
            unique[(claim["gene"], claim["exact_quote"])] = claim
        return list(unique.values())[:20]

    def run(self, context: ToolContext) -> ToolExecution:
        started = time.perf_counter()
        run_id = new_id("tool")
        disease = context.task.context.disease or ""
        genes = context.candidate_genes[:20]
        query = f'"{disease}" AND ({" OR ".join(genes)})' if genes else f'"{disease}"'
        cache_key = hashlib.sha256(query.encode()).hexdigest()[:16]
        cache_path = context.cache_dir / "europe_pmc" / f"{cache_key}.json"
        capability = ToolCapability(
            supported_organisms=["any indexed by Europe PMC"], supported_tissues=["literature-dependent"],
            supported_cell_types=["literature-dependent"], training_scope="not applicable",
            validation_scope="Europe PMC metadata, abstracts and open-access text returned by the API",
        )
        try:
            payload, cached = self._fetch(query, cache_path)
        except (requests.RequestException, ValueError, OSError) as exc:
            return ToolExecution(result=ToolResult(
                tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
                status=ToolStatus.FAILED, coverage_status=CoverageStatus.UNKNOWN, context_match_score=0.0,
                inputs={"query": query}, outputs={}, capability=capability, code_version="2.0.0",
                error=f"Europe PMC retrieval failed: {exc.__class__.__name__}",
                limitations=["No literature claim was emitted because no cached or live source text was available."],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            ), evidence=[])
        results = payload.get("resultList", {}).get("result", [])
        source_meta: dict[str, dict[str, str]] = {}
        chunks = []
        for row in results:
            text = row.get("abstractText") or ""
            source_id = str(row.get("pmid") or row.get("pmcid") or row.get("id") or "")
            if not text or not source_id:
                continue
            uri = f"https://europepmc.org/article/MED/{source_id}" if row.get("pmid") else f"https://europepmc.org/article/PMC/{source_id}"
            source_meta[source_id] = {"uri": uri, "title": row.get("title") or "", "version": str(row.get("firstPublicationDate") or "")}
            chunks.extend(stable_chunks(source_id, text))
        index_path = context.run_dir / "literature_fts.sqlite"
        self._build_index(index_path, chunks)
        recalled = self._recall(index_path, genes)
        extracted = self._llm_extract(disease, genes, recalled)
        backend = "step_span_checked" if extracted else "deterministic_span_checked"
        if not extracted:
            extracted = self._deterministic_extract(disease, genes, recalled)
        by_chunk = {c["chunk_id"]: c for c in recalled}
        evidence = []
        for claim in extracted:
            chunk = by_chunk[claim["chunk_id"]]
            meta = source_meta[chunk["source_id"]]
            quote = claim["exact_quote"]
            start = chunk["text"].index(quote)
            evidence.append(EvidenceItem(
                tool_run_id=run_id, gene_symbol=claim["gene"], claim_class=ClaimClass.FACT,
                statement=claim["statement"],
                source=SourceLocator(
                    uri=meta["uri"], source_id=chunk["source_id"], version=meta["version"],
                    section="abstract", chunk_id=chunk["chunk_id"], start_char=start, end_char=start + len(quote),
                ),
                source_span=quote,
                context=EvidenceContext(disease=disease, assay="literature extraction"),
                stance=claim.get("stance", "uncertain"), effect_direction="unclear", effect={},
                uncertainty="This is a source-grounded literature statement; study design and causal strength require review.",
                quality_flags=["abstract_only"], context_match_score=0.75,
            ))
        coverage = CoverageStatus.COVERED if evidence else CoverageStatus.PARTIAL
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS if evidence else ToolStatus.PARTIAL,
            coverage_status=coverage, context_match_score=0.75 if evidence else 0.4,
            inputs={"query": query, "genes": genes},
            outputs={"search_hits": len(results), "indexed_chunks": len(chunks), "recalled_chunks": len(recalled),
                     "extracted_claims": len(evidence), "extraction_backend": backend,
                     "search_hits_are_evidence": False},
            capability=capability, data_version="EuropePMC:live-or-cache", code_version="2.0.0",
            parameters={"chunk_size": 1200, "chunk_overlap": 150, "recall": "SQLite FTS5 BM25"},
            artifacts=[], evidence_ids=[item.evidence_id for item in evidence],
            warnings=[] if evidence else ["no_span_validated_claims"],
            limitations=["A retrieval hit is not evidence unless a literal span was extracted and validated."],
            cached=cached, elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return ToolExecution(result=result, evidence=evidence)
