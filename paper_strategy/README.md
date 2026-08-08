# Paper Strategy Pattern Library

Paper-to-Strategy (not Paper-to-Workflow): distill how high-quality disease
mechanism / target-discovery studies choose an evidence start, combine lanes,
cross-validate and stop, then store that as a conditional strategy pattern.

## Current status (2026-08-08)

- Contracts: `ObservedWorkflow`, `EvidenceLink`, `StrategyPattern`,
  `BestPracticePattern` in `src/target_agent/paper_strategy.py`.
- PatternStore: append-only JSONL + deterministic lexical retrieval that
  respects task data availability; an optional append-only expert ReviewLedger
  overlays approval status without rewriting immutable pattern records.
- Planner few-shot: `PlannerFewShotBuilder` injects top-k patterns with
  `why_this_order` rationale into the project Planner and the vertical
  domain Planner (LangGraph runtime) when Step is used. The prompt labels the
  hints as strategy-only, never evidence.
- Candidate corpus: 200 metadata-only PubMed records
  (`corpus/corpus.jsonl`, per-record checksums and manifest).
- Curation/extraction toolchain
  (`src/target_agent/pattern_extraction.py`): append-only curation ledger
  (gold/rejected), Europe PMC abstract or bounded methods extraction, strict
  StrategyPattern validation, append-only extraction audit. No full text is
  stored.
- CLI: `target-agent pattern curate|extract|review|search|list` and
  `pattern corpus refresh|status`.
- Regression: `benchmark/pattern_ablation.py` measures offline coverage and
  deterministic plan validity on the public disease gold set; optional
  `--llm` mode compares real Step planner output with and without hints.
- Deferred (P3, per team decision): alignment-data generation and
  Planner/Reviewer small-model training stay last; curated patterns are the
  future training source.

## Paper RAG store

- PaperRagStore (src/target_agent/paper_rag.py) stores bounded abstract chunks
  from the candidate corpus (paper_strategy/rag/chunks.jsonl, per-chunk SHA-256
  digest + MANIFEST). Methods/full text is never persisted.
- Retrieval is deterministic lexical scoring: disease tokens, query tokens,
  available evidence lanes, recency and journal premium. No embeddings and no
  network at query time.
- PlannerFewShotBuilder.build_paper_evidence() injects top chunks into the
  domain Planner and the project ResearchPlanner; hits are stored in
  ResearchPlan.paper_evidence and traced as planner_paper_evidence.
- CLI:
  - target-agent pattern rag refresh --limit 50 (fetch abstracts for corpus
    candidates; use --pmids to select)
  - target-agent pattern rag search --disease "ulcerative colitis" --lanes genetics,omics
  - target-agent pattern rag status
- RAG hits are projected into the mechanism evidence graph as strategy_paper nodes / paper_strategy_hint edges (strategy_only, weight 0, never evidence) and analysed offline via benchmark/pattern_ablation.py --rag; the workbench mechanism panel shows a paper_strategy_hints counter.
  - python scripts/build_paper_rag.py (remote batch refresh; env knobs
    PAPER_RAG_ONLY_GOLD, PAPER_RAG_PMIDS, PAPER_RAG_LIMIT)

## Rules

- Patterns are strategy hints, never evidence for the current task.
- A paper is a Discovery Pattern until expert + benchmark validation promotes
  it to `best_practice` (`BestPracticePattern`).
- Retrieval is deterministic; it never invokes a model or network.
- No full text is stored; only structured abstractions and citations.

## Rebuild

Run `python scripts/build_seed_patterns.py` on the remote test environment to
validate and normalize the pattern library and refresh the manifest.

## Gold paper nomination

- `src/target_agent/gold_nomination.py` deterministically ranks corpus
  candidates as advisory gold-paper nominations: journal premium, query
  bucket, title lane signals (genetics / perturbation / single_cell /
  mechanism / target_drug), RAG ablation gap-disease bonus (UC,
  psoriasis, SLE, ALS, melanoma) and a basic-biology-only penalty.
- Nomination is metadata-only, fully deterministic and never calls a
  model or the network. A nomination never writes to the curation
  ledger; a paper becomes gold only after human reviewers confirm it
  with `target-agent pattern curate`.
- Output: append-ready JSONL + per-line SHA-256 manifest at
  `paper_strategy/nominations.jsonl` / `nominations_MANIFEST.json`.
- CLI: `target-agent pattern nominate --corpus <path> --out <path>
  --limit 40 --min-score 0 --year-min 2021`.

## Curated extraction workflow

1. Refresh the candidate corpus: `target-agent pattern corpus refresh`.
2. Generate an advisory shortlist: `target-agent pattern nominate --limit 40`;
   the ranked list is a curation starting point, not a gold decision.
3. Mark gold papers: `target-agent pattern curate --pmid <PMID> --status gold --rationale "..."
   --role life_science|engineering|lead`.
4. Extract patterns: `target-agent pattern extract` (all gold) or
   `target-agent pattern extract --pmids <PMID1>,<PMID2>`. Requires a
   configured Step provider; each paper is validated against the pattern
   schema before it is appended, and every attempt is recorded in
   `extractions.jsonl`.
5. Review: `target-agent pattern review --pattern-id <id> --role life_science|engineering
   --status approved|rejected`. Approvals are layered from
   `reviews.jsonl`; pattern records are never rewritten.
6. Regress: `python benchmark/pattern_ablation.py` (offline) or
   `python benchmark/pattern_ablation.py --llm --limit 4` (real Step calls).
