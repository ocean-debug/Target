# Decision log

Cross-module contracts, workflow choices, model boundaries and scientific-safety decisions are recorded here. Accepted decisions must not be changed silently in a feature branch.

## 2026-08-01 - Versioned schemas are module boundaries

- **Status:** accepted
- Cross-module objects use the versioned JSON Schemas generated from the canonical Pydantic models.
- Breaking changes require a new contract version and an explicit one-way adapter.
- The goal is to prevent omics, perturbation, evidence and reporting modules from drifting into incompatible field conventions.

## 2026-08-03 - V2 auditable Agent boundaries

- **Status:** superseded in part by V2.1
- This repository is the only maintained implementation; handover assets remain read-only inputs.
- MCH/K562 is an isolated causal-modelling gold sample and must not be presented as disease-context causal evidence.
- Low-context DeltaFactor predictions are exploratory and excluded from formal ranking.
- Reports and the UI render structured Evidence Store values only.
- Experience promotion and LoRA training are offline, auditable and human-approved; automatic code, training or publishing mutation is prohibited.

## 2026-08-03 - V2.1 generic public-omics workflow

- **Status:** accepted
- The public contract is `2.1.0`, with an explicit one-way adapter from TaskSpec `2.0.0`.
- The default disease workflow discovers GEO and CELLxGENE data dynamically; UC snapshots and fixed perturbation tools are disabled compatibility plugins.
- LLMs select only tools exposed by the live typed registry. Matrix type, biological replication, metadata confidence and context remain deterministic gates.
- Cache identity binds source checksums, scientific recipe content, tool and contract versions, and biological context; per-run trace IDs are excluded.
- Infrastructure configuration and secrets are external to Git. The production web command uses Waitress; Flask development mode is explicit.
- Scientific workflow references are pinned to `scientific-agent-skills` v2.62.0 at commit `ad21a3868923628330734375dddbf7b86ea84222`.

## 2026-08-04 - Disease library as a first-class asset

- **Status:** accepted
- `configs/disease_library.yaml` holds 18 curated diseases (autoimmune, neurodegenerative, cancer, metabolic, respiratory); every ontology identifier was verified against live EBI OLS search before entry, and new identifiers must pass the same live check.
- Reference targets are evidence-graded (`approved_drug > gwas > mendelian > clinical_trial > mechanistic`) and serve as ranking sanity anchors, not as ground truth for scoring novelty.
- Task templates encode the project 50/20/15/15 composition (normal / missing_context / conflicting_evidence / trap) with machine-checkable `expectation` blocks consumed by the benchmark layer.
- The disease resolver merges library aliases at runtime; hard-coded legacy aliases win on conflict so existing behaviour never regresses.

## 2026-08-04 - Stable demo replay and live workbench share one backend

- **Status:** accepted
- The main workbench supports both validated stored-run replay and new live Agent runs; replay is never represented as live execution.
- The replay bundle is derived only from persisted status, Plan, Trace, ToolResult, EvidenceItem, ranking and TargetCard artifacts.
- Internal tool/event identifiers, absolute server paths and secrets are excluded from the public bundle.
- Frontend code performs presentation only and does not create new scientific scores, claims or database results.
