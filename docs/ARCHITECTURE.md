# V2.1 architecture and boundaries

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
