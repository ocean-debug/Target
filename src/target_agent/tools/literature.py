"""Europe PMC retrieval, full-text enrichment, persistent corpus and span-checked extraction.

RAG v2.2 upgrades over v2.1:
1. Full-text enrichment — open-access PMC articles are fetched as fullTextXML and
   chunked per section (methods/results/discussion), no longer abstract-only;
2. Persistent shared corpus — chunks accumulate in a cache-dir level FTS5 index
   across runs (current-run sources are still preferred in recall);
3. Optional LLM rerank of recalled chunks before span extraction, with a strict
   BM25 fallback when the LLM is unavailable.

A retrieval hit is never evidence: claims require a literal source span.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests

from ..contracts import (
    ClaimClass, CoverageStatus, EvidenceContext, EvidenceItem, SourceLocator,
    Stance, ToolCapability, ToolDescriptor, ToolResult, ToolStatus, new_id,
)
from ..llm import LLMUnavailable, StepClient
from .base import ScientificTool, ToolContext, ToolExecution


EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPE_PMC_FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"


def stable_chunks(source_id: str, text: str, size: int = 1200, overlap: int = 150,
                  section: str = "abstract") -> list[dict[str, Any]]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        body = cleaned[start:end]
        digest = hashlib.sha256(f"{source_id}:{section}:{start}:{body}".encode()).hexdigest()[:16]
        chunks.append({"chunk_id": f"epmc-{source_id}-{digest}", "source_id": source_id,
                       "section": section, "start": start, "end": end, "text": body})
        if end == len(cleaned):
            break
        start = end - overlap
    return chunks


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_fulltext_sections(xml_text: str) -> list[dict[str, str]]:
    """Split a PMC fullTextXML document into titled sections."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    sections = []
    for sec in root.iter():
        if _localname(sec.tag) != "sec":
            continue
        title = ""
        paragraphs: list[str] = []
        for child in sec.iter():
            name = _localname(child.tag)
            if name == "title" and not title:
                title = "".join(child.itertext()).strip()
            elif name == "p":
                paragraphs.append("".join(child.itertext()).strip())
        body = re.sub(r"\s+", " ", " ".join(p for p in paragraphs if p)).strip()
        if len(body) >= 400:  # 短小节不提供可靠跨句证据
            sections.append({"section": (title or "untitled")[:80], "text": body})
    return sections


class EuropePMCRAGTool(ScientificTool):
    name = "europe_pmc_rag"
    version = "2.2.0"
    descriptor = ToolDescriptor(
        tool_id=name, evidence_dimension="literature",
        description="Retrieve Europe PMC abstracts and open-access full text into a persistent corpus; emit claims only when exact source spans validate.",
        input_types=["TaskSpec", "candidate_genes"], output_types=["EvidenceItem[]"],
        execution_policy="read_only_connector",
    )

    def __init__(self, session: requests.Session | None = None, llm: StepClient | None = None,
                 max_fulltext: int = 3):
        self.session = session or requests.Session()
        self.llm = llm if llm is not None else StepClient.from_env()
        self.max_fulltext = max_fulltext

    def _fetch(self, query: str, cache_path: Path, cache_only: bool = False) -> tuple[dict[str, Any], bool]:
        if cache_only:
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

    def _fetch_fulltext(self, pmcid: str, cache_path: Path, cache_only: bool) -> tuple[str, bool]:
        if cache_only:
            if not cache_path.exists():
                raise FileNotFoundError("full-text cache is missing in cache-only mode")
            return cache_path.read_text(encoding="utf-8"), True
        try:
            response = self.session.get(EUROPE_PMC_FULLTEXT.format(pmcid=pmcid), timeout=45)
            response.raise_for_status()
            text = response.text
            if "<article" not in text:
                raise ValueError("not a fullTextXML document")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")
            return text, False
        except (requests.RequestException, ValueError):
            if cache_path.exists():
                return cache_path.read_text(encoding="utf-8"), True
            raise

    # ---------------- 索引: 运行级审计视图 + 跨运行共享语料 ----------------
    @staticmethod
    def _create_schema(db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5("
                "chunk_id UNINDEXED, source_id UNINDEXED, section UNINDEXED, text)")

    def _build_run_index(self, db_path: Path, chunks: list[dict[str, Any]]) -> None:
        self._create_schema(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM chunks")
            conn.executemany(
                "INSERT INTO chunks(chunk_id, source_id, section, text) "
                "VALUES (:chunk_id, :source_id, :section, :text)", chunks)

    def _update_shared_corpus(self, db_path: Path, chunks: list[dict[str, Any]]) -> int:
        self._create_schema(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO chunks(rowid, chunk_id, source_id, section, text) "
                "VALUES ((SELECT rowid FROM chunks WHERE chunk_id = :chunk_id), "
                ":chunk_id, :source_id, :section, :text)", chunks)
            return conn.execute("SELECT count(*) FROM chunks").fetchone()[0]

    @staticmethod
    def _recall(db_path: Path, genes: list[str], limit: int = 30,
                prefer_sources: set[str] | None = None) -> list[dict[str, str]]:
        if not genes or not db_path.exists():
            return []
        query = " OR ".join(f'"{gene}"' for gene in genes)
        with sqlite3.connect(db_path) as conn:
            if prefer_sources:
                marks = ",".join("?" * len(prefer_sources))
                rows = conn.execute(
                    f"SELECT chunk_id, source_id, section, text FROM chunks WHERE chunks MATCH ? "
                    f"ORDER BY CASE WHEN source_id IN ({marks}) THEN 0 ELSE 1 END, bm25(chunks) LIMIT ?",
                    (query, *sorted(prefer_sources), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT chunk_id, source_id, section, text FROM chunks WHERE chunks MATCH ? "
                    "ORDER BY bm25(chunks) LIMIT ?",
                    (query, limit),
                ).fetchall()
        return [{"chunk_id": r[0], "source_id": r[1], "section": r[2], "text": r[3]} for r in rows]

    # ---------------- LLM 重排(可降级) ----------------
    def _llm_rerank(self, disease: str, genes: list[str],
                    chunks: list[dict[str, str]]) -> tuple[list[dict[str, str]], str]:
        if not self.llm or len(chunks) <= 4:
            return chunks, "bm25_only"
        compact = [{"chunk_id": c["chunk_id"], "text": c["text"][:600]} for c in chunks[:20]]
        system = (
            "Rank text chunks by relevance to explicit disease-gene relationship claims. "
            "Return JSON with key ranked_chunk_ids (most relevant first, subset of supplied ids). "
            "Do not use outside knowledge."
        )
        try:
            payload = self.llm.json_completion(
                system, json.dumps({"disease": disease, "genes": genes, "chunks": compact}))
            ranked_ids = [str(x) for x in payload.get("ranked_chunk_ids", [])]
        except (LLMUnavailable, TypeError, ValueError):
            return chunks, "bm25_fallback_after_llm_error"
        by_id = {c["chunk_id"]: c for c in chunks}
        ordered = [by_id[i] for i in ranked_ids if i in by_id]
        ordered += [c for c in chunks if c["chunk_id"] not in set(ranked_ids)]
        if not ordered:
            return chunks, "bm25_fallback_empty_rerank"
        return ordered, "step_rerank"

    # ---------------- span 校验抽取(v2.1 逻辑保持) ----------------
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
    def _deterministic_extract(
        disease: str, disease_terms: list[str], genes: list[str], chunks: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        normalized_terms = [term.casefold() for term in {disease, *disease_terms} if term]
        claims = []
        for chunk in chunks:
            for sentence in re.split(r"(?<=[.!?])\s+", chunk["text"]):
                lower = sentence.lower()
                gene = next((g for g in genes if re.search(rf"\b{re.escape(g)}\b", sentence, re.I)), None)
                if gene and any(term in lower for term in normalized_terms) and len(sentence) >= 35:
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
        resolver = next((item for item in reversed(context.prior_results) if item.tool_name == "disease_resolver"), None)
        disease = (resolver.outputs.get("normalized_disease") if resolver else None) or context.task.context.disease or ""
        disease_terms = (resolver.outputs.get("search_synonyms") if resolver else None) or [disease]
        genes = context.candidate_genes[:20]
        disease_query = " OR ".join(f'"{term}"' for term in disease_terms[:4])
        query = f'({disease_query}) AND ({" OR ".join(genes)})' if genes else f'({disease_query})'
        cache_key = hashlib.sha256(query.encode()).hexdigest()[:16]
        cache_path = context.cache_dir / "europe_pmc" / f"{cache_key}.json"
        capability = ToolCapability(
            supported_organisms=["any indexed by Europe PMC"], supported_tissues=["literature-dependent"],
            supported_cell_types=["literature-dependent"], training_scope="not applicable",
            validation_scope="Europe PMC metadata, abstracts and open-access full text returned by the API",
        )
        try:
            payload, cached = self._fetch(query, cache_path, context.settings.cache_only)
        except (requests.RequestException, ValueError, OSError) as exc:
            return ToolExecution(result=ToolResult(
                tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
                status=ToolStatus.FAILED, coverage_status=CoverageStatus.UNKNOWN, context_match_score=0.0,
                inputs={"query": query}, outputs={}, capability=capability, code_version="2.2.0",
                error=f"Europe PMC retrieval failed: {exc.__class__.__name__}",
                limitations=["No literature claim was emitted because no cached or live source text was available."],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            ), evidence=[])
        results = payload.get("resultList", {}).get("result", [])
        source_meta: dict[str, dict[str, str]] = {}
        chunks: list[dict[str, Any]] = []
        oa_candidates: list[tuple[str, str]] = []  # (pmcid, title)
        for row in results:
            text = row.get("abstractText") or ""
            source_id = str(row.get("pmid") or row.get("pmcid") or row.get("id") or "")
            if not text or not source_id:
                continue
            uri = f"https://europepmc.org/article/MED/{source_id}" if row.get("pmid") else f"https://europepmc.org/article/PMC/{source_id}"
            source_meta[source_id] = {"uri": uri, "title": row.get("title") or "", "version": str(row.get("firstPublicationDate") or "")}
            chunks.extend(stable_chunks(source_id, text, section="abstract"))
            pmcid = str(row.get("pmcid") or "")
            if pmcid and row.get("isOpenAccess") == "Y":
                oa_candidates.append((pmcid, source_id))
        # ---- 全文增强: 开放获取文章按小节切块(限额, 失败仅记录) ----
        fulltext_articles = 0
        fulltext_errors = 0
        for pmcid, source_id in oa_candidates[: self.max_fulltext]:
            ft_cache = context.cache_dir / "europe_pmc_fulltext" / f"{pmcid}.xml"
            try:
                xml_text, _ = self._fetch_fulltext(pmcid, ft_cache, context.settings.cache_only)
            except (requests.RequestException, ValueError, OSError):
                fulltext_errors += 1
                continue
            sections = parse_fulltext_sections(xml_text)
            if not sections:
                fulltext_errors += 1
                continue
            fulltext_articles += 1
            for sec in sections:
                chunks.extend(stable_chunks(source_id, sec["text"], section=f"fulltext:{sec['section']}"))
        # ---- 运行级审计索引 + 共享语料沉淀 ----
        run_index = context.run_dir / "literature_fts.sqlite"
        self._build_run_index(run_index, chunks)
        shared_index = context.cache_dir / "literature_corpus.sqlite"
        shared_size = self._update_shared_corpus(shared_index, chunks)
        current_sources = {c["source_id"] for c in chunks}
        recalled = self._recall(shared_index, genes, prefer_sources=current_sources)
        recalled, rerank_backend = self._llm_rerank(disease, genes, recalled)
        extracted = self._llm_extract(disease, genes, recalled)
        backend = "step_span_checked" if extracted else "deterministic_span_checked"
        if not extracted:
            extracted = self._deterministic_extract(disease, disease_terms, genes, recalled)
        by_chunk = {c["chunk_id"]: c for c in recalled}
        evidence = []
        for claim in extracted:
            chunk = by_chunk[claim["chunk_id"]]
            meta = source_meta.get(chunk["source_id"])
            if meta is None:  # 共享语料中的历史来源: 用注册 URI 兜底, 仍要求 chunk 内 span 命中
                meta = {"uri": f"https://europepmc.org/article/MED/{chunk['source_id']}",
                        "title": "", "version": "shared-corpus"}
            quote = claim["exact_quote"]
            start = chunk["text"].index(quote)
            section = chunk.get("section", "abstract")
            flags = ["abstract_only"] if section == "abstract" else [section[:60]]
            evidence.append(EvidenceItem(
                tool_run_id=run_id, gene_symbol=claim["gene"], claim_class=ClaimClass.FACT,
                statement=claim["statement"],
                source=SourceLocator(
                    uri=meta["uri"], source_id=chunk["source_id"], version=meta["version"],
                    section=section, chunk_id=chunk["chunk_id"], start_char=start, end_char=start + len(quote),
                ),
                source_span=quote,
                context=EvidenceContext(disease=disease, assay="literature extraction"),
                stance=claim.get("stance", "uncertain"), effect_direction="unclear", effect={},
                uncertainty="This is a source-grounded literature statement; study design and causal strength require review.",
                quality_flags=flags, context_match_score=0.75 if section == "abstract" else 0.85,
            ))
        coverage = CoverageStatus.COVERED if evidence else CoverageStatus.PARTIAL
        result = ToolResult(
            tool_run_id=run_id, tool_name=self.name, tool_version=self.version,
            status=ToolStatus.SUCCESS if evidence else ToolStatus.PARTIAL,
            coverage_status=coverage, context_match_score=0.75 if evidence else 0.4,
            inputs={"query": query, "genes": genes},
            outputs={"search_hits": len(results), "indexed_chunks": len(chunks),
                     "fulltext_articles": fulltext_articles, "fulltext_errors": fulltext_errors,
                     "shared_corpus_chunks": shared_size,
                     "recalled_chunks": len(recalled), "rerank_backend": rerank_backend,
                     "extracted_claims": len(evidence), "extraction_backend": backend,
                     "search_hits_are_evidence": False},
            capability=capability, data_version="EuropePMC:live-or-cache", code_version="2.2.0",
            parameters={"chunk_size": 1200, "chunk_overlap": 150,
                        "recall": "SQLite FTS5 BM25 over persistent shared corpus",
                        "rerank": "optional Step LLM rerank with BM25 fallback",
                        "fulltext": f"open-access fullTextXML, <= {self.max_fulltext} articles"},
            artifacts=[], evidence_ids=[item.evidence_id for item in evidence],
            warnings=[] if evidence else ["no_span_validated_claims"],
            limitations=["A retrieval hit is not evidence unless a literal span was extracted and validated.",
                         "Full-text enrichment covers at most the first open-access hits per run."],
            cached=cached, elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return ToolExecution(result=result, evidence=evidence)
