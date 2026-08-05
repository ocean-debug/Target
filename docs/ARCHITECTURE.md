# TargetDiscovery Agent V3 architecture and boundaries

Target is a vertical disease-target-discovery Agent. V3 adds a project-level reliability control plane beneath that product surface. A project, execution run and artifact are first-class records so a multi-step target investigation can survive sessions, failures and review; chat history is not the system of record.

```text
Target research question + TaskSpec
  -> target-specific Project Planner
  -> frozen WorkItem DAG + typed input/output contracts
  -> recoverable execution through an allowlisted target-tool registry
  -> content-addressed Artifacts + append-only Events and Decisions
  -> target-evidence synthesis + separate digest-bound Assessment
  -> Reviewer findings -> bounded connector retry / human checkpoint
  -> release gate -> ranked targets, TargetCards and falsifiable experiments
```

The internal project layer owns goal continuity, work-item dependencies, acceptance criteria, artifact lineage, recovery and release state. The target-discovery layer remains authoritative for biological context, evidence semantics, ranking, blockers and causal boundaries. The generic-looking project objects are infrastructure, not a promise that arbitrary life-science workflows are supported.

## Disease-to-target domain workflow

```text
TaskSpec 2.2
  -> Step JSON Planner / deterministic generic fallback
  -> typed allowlisted Router
  -> disease resolver
  -> GEO search -> metadata audit -> recipe -> bulk analysis
  -> CELLxGENE discovery / standard H5AD or 10x donor-level pseudobulk
  -> GSEA + ORA with tested-gene background
  -> optional pre-staged GWAS audit -> precomputed SuSiE credible-set audit -> precomputed coloc regional audit
  -> Open Targets aggregate associations + Europe PMC
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
- **Domain observability:** the child Trace remains the scientific execution truth. A separate,
  append-only activity ledger exposes only stage, tool status, coverage and source IDs through its
  own cursor. It never copies candidate genes, evidence statements, scores or Reviewer prose.
- **Recovery:** work-item completion is checkpointed. Resume uses persisted terminal results and never guesses whether an interrupted side effect succeeded.
- **Review and repair:** structural checks are separate from scientific judgment. Reviewer findings are bound to a target digest and may recommend a dataset switch, evidence supplementation or replan; current automatic execution is limited to bounded retries of failed allowlisted read-only connectors. Deterministic gates remain authoritative.
- **Transient repair boundary:** only failed allowlisted read-only connectors are automatically retried. The Reviewer runs again on each tool's latest attempt; all earlier attempts remain auditable. Scientific ineligibility, context mismatch and unsupported causal scope cannot be cleared by retry.
- **Human control:** supervised or checkpointed projects may pause before execution, high-risk interpretation, goal change or release. An override is an explicit decision, never a hidden flag.

## Vertical capability boundary

V2.2 provides the deepest implemented disease-to-target chain: dynamic public-data discovery, controlled omics analysis, a checksum-bound precomputed GWAS/SuSiE/coloc audit lane, Open Targets aggregate context, literature/trials evidence, ranking, TargetCards, review and traceable reporting. V3 phase one adds the durable project store, module registry, typed planning and recovery layer around that chain.

Allowlisted statistical recomputation of fine-mapping/colocalization, broadly matched perturbation Oracles, external blind ranking evaluation and scaled expert approval operations are still roadmap items. A phase-one stdio MCP adapter now exposes the durable project service and verified text artifacts to external Agent hosts; Streamable HTTP MCP, registry publication and host-specific installation bundles remain roadmap work. Unsupported evidence lanes remain `needs_input`, `not_covered` or `completed_with_gaps`; they are never represented as complete.

## Runtime and domain-service boundary

Target does not attempt to replace a mature scientific workbench. Codex, SciForge, OpenScience,
OpenAI4S or Wisp may own chat, files, general code execution, remote compute and user interaction.
Target owns the disease-target contract, typed project lifecycle, allowlisted scientific modules,
evidence gates, Reviewer decisions, immutable artifacts and release semantics. HTTP, CLI and MCP
are adapters over those records rather than independent Agent implementations.

The MCP adapter exposes create/run/status/event/domain-activity/checkpoint/artifact operations through
`ResearchProjectService`. A host may stop after any human checkpoint and resume later without
reconstructing state from conversation history. It cannot use MCP to bypass a frozen plan,
artifact digest, biological-context gate or terminal evidence gap.

See [PRODUCT_V3.md](PRODUCT_V3.md) and [research_project.yaml](../workflows/research_project.yaml) for the product boundary and internal target-project workflow.
