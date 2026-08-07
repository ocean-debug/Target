# TargetDiscovery Agent V3

## Product position

Target is a vertical Agent for disease-driven drug-target discovery. A user supplies a disease question and biological context; the system plans the investigation, acquires and analyses evidence, ranks candidate targets, exposes conflicts and gaps, and proposes falsifiable validation experiments.

The product is not a general-purpose scientific workbench. The V3 project/run/artifact model is internal reliability infrastructure for long-running target research. It keeps the accepted goal, evidence snapshots, tool runs, decisions and reviews coherent across retries and sessions.

## Intended output

For a disease, subtype, tissue, cell type, stage and desired phenotype, the product should deliver:

- a ranked candidate list whose score is an evidence-priority score, never a clinical success probability;
- a TargetCard for each priority candidate, with supporting and opposing evidence kept separate;
- traceable genetics, disease-context omics, perturbation, mechanism, druggability, drug and safety evidence;
- explicit `FACT`, `OBSERVED`, `PREDICTED` and `INFERRED` labels;
- a `GO`, `CONDITIONAL_GO` or `INSUFFICIENT_EVIDENCE` recommendation under deterministic gates;
- a falsifiable experiment plan whose positive, negative and contradictory outcomes map to different conclusions;
- a machine-readable evidence package and a human-readable report, both bound to exact source and artifact versions.

## Defensible product moat

### 1. Real and diverse alignment data

Alignment data should come from actual target-research decisions and failure modes, not only synthetic question-answer pairs. The dataset must cover multiple disease classes, evidence availability levels, negative and conflicting evidence, context mismatch, tool failure, causal overreach and correct refusal. Planner, evidence extraction and Reviewer examples should preserve source spans and tool-run lineage. Only expert-approved cases can be promoted into training or workflow templates.

Current status: the repository has structured Planner/Reviewer training assets, disease-library cases and fake/unit/live benchmark modes. The externally stored Reviewer adapter used in prior acceptance covers the earlier generic V2.1 failure taxonomy; its weights are not tracked in Git. V2.2 genetics-specific examples still require separate scientific and engineering review and retraining. The current assets do not yet constitute a large, externally audited cross-disease alignment corpus.

### 2. Target-specific evidence contracts

The public contract is more valuable than a fluent report. `TaskSpec`, `ToolResult`, `EvidenceItem`, `Claim`, `ReviewerFinding`, ranking components, blockers, `TargetCard` and `ExperimentPlan` encode the scientific distinctions needed for target decisions. Biological context, coverage, provenance and uncertainty are required fields rather than optional prose.

Current status: contract `2.2.0`, generated schemas, append-only Evidence Store and trace/report linkage are implemented for the existing target-discovery runtime. V3 project contracts add durable work-item, artifact, assessment and decision records around that runtime.

### 3. Unified multi-evidence target graph

The target view should join six evidence lanes without erasing their differences:

```text
controlled GWAS inputs + supplied precomputed eQTL/coloc outputs
              + disease-context bulk and single-cell omics
              + observed and predicted perturbation
              + literature and mechanism convergence
              + druggability / drugs / trials
              + safety and translational feasibility
              -> target evidence graph -> ranking + blockers
```

Current status: dynamic GEO/CELLxGENE discovery, controlled bulk/single-cell workflows, Europe PMC RAG, ClinicalTrials.gov and scoped perturbation plugins exist. Contract 2.2 adds controlled GWAS summary-statistics ingestion plus audits of precomputed SuSiE signal credible sets and precomputed coloc results with checksum-bound variant-level harmonization manifests. These statistical posteriors remain `INFERRED`; Open Targets aggregates are non-formal context and somatic mutation is not conflated with inherited genetics. Statistical fine-mapping/coloc recomputation and broadly applicable perturbation Oracles remain roadmap work. Context-mismatched DeltaFactor/K562 results must not enter formal disease ranking.

### 4. Reviewer that repairs, not only scores

The Reviewer should detect missing provenance, invalid sample grouping, context mismatch, contradictory evidence, unsupported causal language, numeric inconsistency and incomplete outputs. An actionable finding can recommend alternate-dataset selection, evidence supplementation or replan. A deterministic scientific gate cannot be waived by the LLM.

Current status: deterministic review, optional structured LLM/LoRA confirmation and two bounded repair layers exist. The child workflow can retry allowlisted read-only connectors. The project control plane can turn a project execution/integrity assessment of a typed transient failure in a side-effect-free and replay-safe module into an immutable `RepairRequest`, append a same-input execution overlay, recompute the affected successor subgraph, rerun that assessment and bind the release decision marker to the new active snapshot. Domain scientific findings do not yet trigger project-level evidence repair. Historical results, assessments and artifacts remain auditable. Invalid matrices, context mismatch, OOD models, method changes and scientific coverage gaps are never “repaired” by retry. Dataset switching and general repair across evidence lanes remain roadmap capabilities.

### 5. Blind ranking benchmark and expert audit

Quality is measured by whether the Agent prioritizes defensible targets and rejects traps on unseen cases, not by whether a report looks complete. A durable benchmark needs hidden disease cases, frozen data snapshots, target-ranking relevance labels, blocker expectations, reproducibility checks and blinded expert adjudication.

Current status: the repository includes a systematic internal benchmark and disease gold tasks for contracts, robustness, determinism, recovery and engine parity. A reference score-only protocol now freezes task, ranking and terminal-status digests before loading Git-external labels and reports disease-macro nDCG/Recall/MRR plus non-compensating trap and safety gates. The public 18-disease reference library is explicitly ineligible as a final blind set. No evaluator-controlled scorer, independent external expert-adjudicated label set or blind biological performance result exists yet, and internal benchmark scores must not be marketed as biological discovery performance.

### 6. Falsifiable experiments and expert release

Every priority TargetCard should state what experiment is most informative next, what controls are required, and how positive, negative and contradictory results change the decision. High-risk recommendations require life-science expert approval bound to the exact evidence snapshot.

Current status: structured experiment plans and deterministic recommendation gates exist. The system proposes experiments but does not run wet-lab work. A scaled expert-review queue, adjudication UI and audited release operation are not yet complete.

### 7. Product embedding through API and MCP

The Agent should be usable inside an existing scientist workbench: submit a target question, stream plan/run events, inspect evidence and Reviewer findings, download artifacts and resume a project. The same typed operations should be exposed through HTTP and MCP rather than forcing users into a standalone chat UI.

Current status: the HTTP workbench provides run creation, status, SSE, reports and artifacts for the V2.2 workflow. V3 adds project creation, status, event-ledger, domain-activity, content-addressed artifact, repair-queue and snapshot-bound repair-decision endpoints. An optional official-SDK stdio MCP server exposes the same durable project service through eleven typed tools, including repair inspection and approval/rejection. Domain activities are source-linked operational projections and never copy target rankings or evidence content. Streamable HTTP MCP, registry publication, authentication policy for remote MCP and host-specific installation bundles remain roadmap work.

## V3 reliability control plane

The internal V3 control plane adapts proven ideas from SciForge, OpenScience, OpenAI4S and Wisp without importing their code:

- project, run and artifact are first-class records rather than chat attachments;
- accepted evidence and report artifacts are immutable, content-addressed snapshots;
- events, assessments and decisions are append-only;
- work items have typed inputs, outputs, dependencies, success criteria and stopping conditions;
- execution checkpoints after bounded work so restart does not guess what happened;
- a separate assessment/review stage is bound to an exact artifact digest;
- autonomous, checkpointed and supervised modes place explicit human approval points.

These mechanisms serve one product outcome: a more reliable disease-target decision package.

## Current V3 phase-one scope

The current increment includes typed project/goal/work-item/plan/result/artifact/assessment/decision records, a filesystem project store, allowlisted module registry, constrained planner, work-item recovery, structural assessments and a target-discovery adapter. It also adds immutable repair requests, append-only plan-revision overlays, typed repair resolutions, exact-snapshot approvals and release-decision-marker rebinding. The project reconciles a paged domain-activity index before and after child execution so tool coverage and repair lineage are observable without duplicating the child Evidence Store. The V2.2 workflow remains the scientific engine and deepest product path.

Phase one does not provide arbitrary LLM-generated Python/R/shell execution, universal life-science workflow coverage, automatic wet-lab control, self-modifying code, automatic training, clinical decision support or scientific independence when one model produces and reviews the same claim.

## Execution integrity status (2026-08-08)

The work-item execution path now treats leases and attempts as durable, auditable state:

- `_execute_one` acquires a bounded `WorkerLease` (default 4h) before executing and always releases it in `finally`. Orphan leases (no attempt, or attempt already terminal) are reclaimed and recorded as `lease_reclaimed`; a live `RUNNING`/`PENDING` attempt on the same item raises `ProjectBusyError` instead of double-executing.
- Every completed execution appends an immutable `WorkAttempt` (`attempt-<hex>` id, contiguous attempt number, output digest, lease id and supersedes chain). On resume, `_reconcile_attempt_ledger()` backfills cancelled ledger rows so numbering never jumps.
- `read_leases()` returns the latest snapshot per lease id from the append-only JSONL, so an active and a released snapshot of the same lease never coexist.
- Dataset candidates are read canonically from `tool_results.jsonl` (fallback to `report.json`), normalized to `candidate`/`rejected` statuses with `context_match_score`, sample counts and processed files, and deduplicated by accession with tool results taking precedence. This keeps dataset switching and Reviewer-driven re-selection consistent within the same project context.
- Schema export is verified end to end: 52 canonical JSON Schemas including `research_work_attempt`, `research_worker_lease`, `research_fork_directive` and `research_plan_branch`. `python -m target_agent.cli` now works (module entry guard added); `target-agent` remains the documented entry point.
- Regression: full suite 257 passed / 2 skipped on the remote acceptance environment.

Arbitrary step rollback is now implemented as `ForkDirective` + `PlanBranch` + `fork_rollback` plan overlays:

- `redo` replaces the target item and its transitive dependants with fresh item ids bound to the branch and re-executes them; `input_overrides` are limited to affected items and frozen in the immutable directive.
- `restore` replays an immutable historical `WorkAttempt` result snapshot without re-running the step, then re-runs only its dependants. A restore may target the original logical step even after a fork replaced it: the service resolves the unique active representative and re-binds the snapshot to that item with `supersedes_result_digest` provenance, keeping the attempt snapshot as the source of truth.
- Every branch is bound to an exact project snapshot digest; a stale directive pauses the project instead of applying. `checkpointed` projects and every `restore` require human approval (`decide_fork`), while `autonomous` redo forks auto-approve. Fork budget is independent of the repair budget (`max_forks`), and plan revisions are capped at 30.
- `assert_integrity()` verifies branch chain continuity, directive/branch one-to-one binding, fork revision digests, restore attempt lineage and normalized restored-result digests, and rejects tampering.
- Web API exposes `POST /api/projects/<id>/forks`, `GET /api/projects/<id>/branches` and `POST /api/projects/<id>/forks/<branch_id>/decision`; MCP exposes `target_propose_fork`, `target_decide_fork` and `target_get_branches`.

The Web workbench is now a wired project console rather than a static mock:

- `GET /api/projects` lists durable projects; `POST /api/projects/<id>/resume` manually continues a paused project.
- The single-page workbench (rewritten with correct UTF-8 Chinese) supports creating a project (disease, subtype, tissue, cell type, stage, phenotype, approval mode), checkpoint approvals (`plan`/`release`), repair/fork approve-or-reject, and arbitrary-step rollback: `redo` with `input_overrides`, `restore` with historical-attempt selection and lineage-aware re-binding.
- Results, branches, events and artifacts render only from backend APIs; the page never fabricates numbers.
- End-to-end HTTP smoke on the remote acceptance environment passed: create project → approve plan → real tool execution (GEO search, omics analysis, Europe PMC, Open Targets, ClinicalTrials) → terminal `completed_with_gaps` with honest degradation → events/artifacts/project list all present.

Paper-to-Strategy (P0/P1) is delivered: `paper_strategy.py` defines immutable `ObservedWorkflow` / `StrategyPattern` / `BestPracticePattern` contracts, an append-only deterministic `PatternStore` and `PlannerFewShotBuilder`; the seed corpus has 10 curated discovery patterns with a checksum manifest. Patterns are strategy hints, never task evidence, until expert + benchmark validation promotes them to `best_practice`. P3 alignment-data generation and Planner/Reviewer LoRA training are deferred to the final phase per team decision.

## Release gate

A target project may be `completed` only when all required work items satisfy their contracts, required artifacts pass hash validation, no blocking scientific finding remains, and ranked candidates, required TargetCards and the declared report exist. Otherwise the project must return `completed_with_gaps`, `needs_input` or `failed` with the missing evidence and next action; a domain tool may separately record `refused` for an out-of-scope request. Tool-call count, LLM confidence and polished prose are not completion criteria.
