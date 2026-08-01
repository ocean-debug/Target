# Agent Instructions

## Project objective

Build a traceable life-science research Agent for disease-driven drug target discovery. The product is an Agent, not a standalone evaluation platform.

## Non-negotiable scientific rules

- Never fabricate papers, datasets, identifiers, measurements or model results.
- Distinguish `FACT`, `OBSERVED`, `PREDICTED` and `INFERRED` claims.
- Do not present correlation as causation or model prediction as experimental fact.
- Preserve organism, tissue, cell type, disease stage, assay and perturbation context.
- Reject or degrade results outside a model's documented training and validation scope.
- Every material claim must trace to an EvidenceItem or ToolResult.

## Engineering rules

- Treat `schemas/` and `workflows/` as shared contracts.
- Make small, scoped changes; do not refactor unrelated modules.
- Do not add dependencies without documenting why they are necessary.
- Never commit secrets, patient information, large biological data, model weights, caches or absolute local paths.
- Every tool needs a success example, a failure/OOD example, provenance, warnings and limitations.
- A module is complete only after the main Agent calls it and a non-author reproduces it.

## Collaboration

- Read `docs/OWNERSHIP.md` before editing another member's primary module.
- Record cross-module decisions in `DECISION_LOG.md`.
- Update affected schemas, examples and documentation in the same PR.
- Scientific PRs require scientific review; shared interfaces require engineering review.
