# TargetDiscovery Agent V3 architecture and boundaries

Target is a vertical disease-target-discovery Agent. V3 adds a project-level reliability control plane beneath that product surface. A project, execution run and artifact are first-class records so a multi-step target investigation can survive sessions, failures and review; chat history is not the system of record.

```text
Target research question + TaskSpec
  -> target-specific Project Planner
  -> frozen WorkItem DAG + typed input/output contracts
  -> recoverable execution through an allowlisted target-tool registry
  -> content-addressed Artifacts + append-only Events and Decisions
  -> target-evidence synthesis + independent Assessment
  -> Reviewer repair / human checkpoint when required
  -> release gate -> ranked targets, TargetCards and falsifiable experiments
```

The internal project layer owns goal continuity, work-item dependencies, acceptance criteria, artifact lineage, recovery and release state. The target-discovery layer remains authoritative for biological context, evidence semantics, ranking, blockers and causal boundaries. The generic-looking project objects are infrastructure, not a promise that arbitrary life-science workflows are supported.

## Disease-to-target domain workflow

```text
TaskSpec 2.1
  -> Step JSON Planner / deterministic generic fallback
  -> typed allowlisted Router
  -> disease resolver
  -> GEO search -> metadata audit -> recipe -> bulk analysis
  -> CELLxGENE discovery / standard H5AD or 10x donor-level pseudobulk
  -> GSEA + ORA with tested-gene background + Open Targets + Europe PMC
  -> append-only Evidence Store + Trace + checkpoints
  -> deterministic Reviewer + additive Step Reviewer and bounded replan
  -> six-dimensional ranking + independent blockers
  -> mechanistic evidence graph / MCH-only causal graph
  -> TargetCards + falsifiable experiments + report
```

The Agent never runs arbitrary generated code. LLM output can propose only tools present in the live registry and cannot waive deterministic scientific gates.

`FACT`, `OBSERVED`, `PREDICTED` and `INFERRED` remain separate. Disease omics is observational; MCH/K562 is the only causal gold configuration. The frontend renders backend artifacts and performs no scientific calculation.

## Product-specific reliability model

- **Goal continuity:** the accepted goal and success criteria are versioned project records; any reframing requires a recorded decision.
- **Target evidence contracts:** each work item declares typed inputs, outputs and acceptance criteria; every material target claim must retain its disease, tissue, cell, stage, assay and perturbation context.
- **Evidence and artifacts:** deliverables point to immutable, hashed artifact versions. Replacing a file creates a new version rather than rewriting history.
- **Auditability:** project events, assessments and decisions are append-only. A snapshot is a materialized view, not the audit source.
- **Recovery:** work-item completion is checkpointed. Resume uses persisted terminal results and never guesses whether an interrupted side effect succeeded.
- **Review and repair:** structural checks are separate from scientific judgment. Reviewer findings are bound to a target digest and may trigger a bounded dataset switch, evidence supplementation or replan; deterministic gates remain authoritative.
- **Transient repair boundary:** only failed allowlisted read-only connectors are automatically retried. The Reviewer runs again on each tool's latest attempt; all earlier attempts remain auditable. Scientific ineligibility, context mismatch and unsupported causal scope cannot be cleared by retry.
- **Human control:** supervised or checkpointed projects may pause before execution, high-risk interpretation, goal change or release. An override is an explicit decision, never a hidden flag.

## Vertical capability boundary

V2.1 already provides the deepest implemented disease-to-target chain: dynamic public-data discovery, controlled omics analysis, Open Targets, literature/trials evidence, ranking, TargetCards, review and traceable reporting. V3 phase one adds the durable project store, module registry, typed planning and recovery layer around that chain.

User-supplied GWAS fine-mapping/eQTL colocalization, broadly matched perturbation Oracles, external blind ranking evaluation, scaled expert approval operations and MCP publication are still roadmap items. Unsupported evidence lanes remain `needs_input`, `not_covered` or `completed_with_gaps`; they are never represented as complete.

See [PRODUCT_V3.md](PRODUCT_V3.md) and [research_project.yaml](../workflows/research_project.yaml) for the product boundary and internal target-project workflow.
