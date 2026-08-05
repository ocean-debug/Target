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

Current status: the repository has structured Planner/Reviewer training assets, disease-library cases and fake/unit/live benchmark modes. It does not yet constitute a large, externally audited cross-disease alignment corpus.

### 2. Target-specific evidence contracts

The public contract is more valuable than a fluent report. `TaskSpec`, `ToolResult`, `EvidenceItem`, `Claim`, `ReviewerFinding`, ranking components, blockers, `TargetCard` and `ExperimentPlan` encode the scientific distinctions needed for target decisions. Biological context, coverage, provenance and uncertainty are required fields rather than optional prose.

Current status: contract `2.1.0`, generated schemas, append-only Evidence Store and trace/report linkage are implemented for the existing target-discovery runtime. V3 project contracts add durable work-item, artifact, assessment and decision records around that runtime.

### 3. Unified multi-evidence target graph

The target view should join six evidence lanes without erasing their differences:

```text
human genetics / GWAS / eQTL
              + disease-context bulk and single-cell omics
              + observed and predicted perturbation
              + literature and mechanism convergence
              + druggability / drugs / trials
              + safety and translational feasibility
              -> target evidence graph -> ranking + blockers
```

Current status: Open Targets genetics/association/drug evidence, dynamic GEO/CELLxGENE discovery, controlled bulk/single-cell workflows, Europe PMC RAG, ClinicalTrials.gov and scoped perturbation plugins exist. Dedicated ingestion of user GWAS summary statistics, fine-mapping, eQTL colocalization and broadly applicable perturbation Oracles remain to be implemented. Context-mismatched DeltaFactor/K562 results must not enter formal disease ranking.

### 4. Reviewer that repairs, not only scores

The Reviewer should detect missing provenance, invalid sample grouping, context mismatch, contradictory evidence, unsupported causal language, numeric inconsistency and incomplete outputs. An actionable finding can trigger a bounded alternate-dataset selection, evidence supplementation or replan. A deterministic scientific gate cannot be waived by the LLM.

Current status: deterministic review, optional structured LLM/LoRA confirmation and bounded repair exist. A failed allowlisted read-only connector (GEO search, CELLxGENE discovery, Open Targets, Europe PMC or ClinicalTrials.gov) can be retried within the declared tool/review budget and is then independently re-reviewed. Historical failed attempts remain in the ledger, while release uses the latest effective attempt. Invalid matrices, context mismatch, OOD models and scientific coverage gaps are never “repaired” by retry. General repair across every evidence lane remains a roadmap capability.

### 5. Blind ranking benchmark and expert audit

Quality is measured by whether the Agent prioritizes defensible targets and rejects traps on unseen cases, not by whether a report looks complete. A durable benchmark needs hidden disease cases, frozen data snapshots, target-ranking relevance labels, blocker expectations, reproducibility checks and blinded expert adjudication.

Current status: the repository includes a systematic internal benchmark and disease gold tasks for contracts, robustness, determinism, recovery and engine parity. A reference score-only protocol now freezes task, ranking and terminal-status digests before loading Git-external labels and reports disease-macro nDCG/Recall/MRR plus non-compensating trap and safety gates. The public 18-disease reference library is explicitly ineligible as a final blind set. No evaluator-controlled scorer, independent external expert-adjudicated label set or blind biological performance result exists yet, and internal benchmark scores must not be marketed as biological discovery performance.

### 6. Falsifiable experiments and expert release

Every priority TargetCard should state what experiment is most informative next, what controls are required, and how positive, negative and contradictory results change the decision. High-risk recommendations require life-science expert approval bound to the exact evidence snapshot.

Current status: structured experiment plans and deterministic recommendation gates exist. The system proposes experiments but does not run wet-lab work. A scaled expert-review queue, adjudication UI and audited release operation are not yet complete.

### 7. Product embedding through API and MCP

The Agent should be usable inside an existing scientist workbench: submit a target question, stream plan/run events, inspect evidence and Reviewer findings, download artifacts and resume a project. The same typed operations should be exposed through HTTP and MCP rather than forcing users into a standalone chat UI.

Current status: the HTTP workbench provides run creation, status, SSE, reports and artifacts for the V2.1 workflow. V3 phase one adds project creation, project status, event-ledger and content-addressed artifact endpoints. API versioning/hardening and MCP exposure remain roadmap work; no current document should claim MCP as shipped.

## V3 reliability control plane

The internal V3 control plane adapts proven ideas from SciForge, OpenScience, OpenAI4S and Wisp without importing their code:

- project, run and artifact are first-class records rather than chat attachments;
- accepted evidence and report artifacts are immutable, content-addressed snapshots;
- events, assessments and decisions are append-only;
- work items have typed inputs, outputs, dependencies, success criteria and stopping conditions;
- execution checkpoints after bounded work so restart does not guess what happened;
- independent review is bound to an exact artifact digest;
- autonomous, checkpointed and supervised modes place explicit human approval points.

These mechanisms serve one product outcome: a more reliable disease-target decision package.

## Current V3 phase-one scope

The first increment introduces typed project/goal/work-item/plan/result/artifact/assessment/decision records, a filesystem project store, allowlisted module registry, constrained planner, work-item recovery, structural assessments and a target-discovery adapter. The existing V2.1 workflow remains the scientific engine and the deepest validated path.

Phase one does not provide arbitrary LLM-generated Python/R/shell execution, universal life-science workflow coverage, automatic wet-lab control, self-modifying code, automatic training, clinical decision support or scientific independence when one model produces and reviews the same claim.

## Release gate

A target project may be `completed` only when all required work items satisfy their contracts, required artifacts pass hash validation, no blocking scientific finding remains, and ranked candidates, required TargetCards and the declared report exist. Otherwise the project must return `completed_with_gaps`, `needs_input` or `failed` with the missing evidence and next action; a domain tool may separately record `refused` for an out-of-scope request. Tool-call count, LLM confidence and polished prose are not completion criteria.
