# Paper Strategy Pattern Library

Paper-to-Strategy (not Paper-to-Workflow): distill how high-quality disease
mechanism / target-discovery studies choose an evidence start, combine lanes,
cross-validate and stop, then store that as a conditional strategy pattern.

## Current status (2026-08-08)

- Contracts: `ObservedWorkflow`, `EvidenceLink`, `StrategyPattern`,
  `BestPracticePattern` in `src/target_agent/paper_strategy.py`.
- PatternStore: append-only JSONL + deterministic lexical retrieval that
  respects task data availability.
- Planner few-shot: `PlannerFewShotBuilder` injects top-k patterns with
  `why_this_order` rationale into the project Planner when Step is used.
- Seed corpus: 10 curated discovery patterns in `patterns.jsonl`
  (`MANIFEST.json` has per-line checksums).
- Deferred (P3, per team decision): alignment-data generation and
  Planner/Reviewer small-model training.

## Rules

- Patterns are strategy hints, never evidence for the current task.
- A paper is a Discovery Pattern until expert + benchmark validation promotes
  it to `best_practice` (`BestPracticePattern`).
- Retrieval is deterministic; it never invokes a model or network.
- No full text is stored; only structured abstractions and citations.

## Rebuild

Run `python scripts/build_seed_patterns.py` on the remote test environment to
validate and normalize the corpus and refresh the manifest.
