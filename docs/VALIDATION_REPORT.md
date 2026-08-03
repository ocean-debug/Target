# V2.1 validation report

This file records portable acceptance facts only. Infrastructure identifiers are retained in the external execution profile and private job logs.

## Required checks

- [x] Contract and generated-schema consistency.
- [x] Explicit 2.0-to-2.1 TaskSpec migration and mixed-version rejection.
- [x] Generic Planner uses the live typed registry.
- [x] `.env` auto-loading and process-environment precedence.
- [x] Step structured planning without fallback, including request metadata.
- [x] Dynamic GEO discovery and metadata eligibility gates.
- [x] PyDESeq2 rejection of continuous/non-integer expression.
- [x] Single-cell donor/pseudobulk metadata gates and synthetic execution.
- [x] Evidence-to-ToolRun-to-Trace referential integrity.
- [x] Missing omics data returns `completed_with_gaps` while other evidence chains continue.
- [x] Formal Waitress launch plus live health and capabilities endpoints.
- [x] Repository contains no secret or infrastructure-specific value.

## Latest portable evidence

- 33 remote-node tests passed, including unfinished-run identity recovery, stable checksum-bound cache keys, one bounded structured-output repair, request-ID capture, generic Planner routing, non-integer DESeq rejection and donor-level pseudobulk execution.
- Repository policy scan passed and all 16 generated JSON Schemas contain contract `2.1.0` only.
- Alignment factory produced 120 SFT cases, 60 preference pairs and 30 held-out acceptance cases with dual-review gates.
- Live cold-search probes discovered disease-specific GEO candidates for Alzheimer disease and lung adenocarcinoma without an accession in TaskSpec.
- GSE318560 completed an Alzheimer-disease PyDESeq2 run; GSE104854 completed the independent lung-adenocarcinoma gold-input PyDESeq2 run.
- Alzheimer disease selected GSE248417/GSE318560 dynamically: cold run 47 seconds; cached runs 20, 7 and 5 seconds with identical status and rankings.
- Lung adenocarcinoma selected GSE310170 dynamically: cold run 79 seconds; cached runs 19, 8 and 8 seconds with identical status and rankings.
- UC selected GSE177044 dynamically but had no eligible automatic bulk result, so it correctly returned `completed_with_gaps`; cached runs took 7, 7 and 6 seconds with identical status and rankings.
- A scheduled-node Waitress process passed live `/healthz` and `/api/capabilities` checks using the externally supplied loopback bind and service port; the process was stopped after acceptance.
- A real Step 3.7 Flash smoke test produced a valid 14-step plan without fallback in 23.0 seconds; the provider request ID was captured without exposing the API key.

## Current environment-specific gaps

- The validated node exposes Scanpy 1.11.5 and AnnData 0.12.16. Its operating-system ABI has no compatible TileDB-SOMA wheel required by `cellxgene-census==1.17.*`, so Census is correctly reported unavailable rather than silently downgraded.
- The optional fixed limma backend is not declared ready because neither Rscript nor the limma package is present.

The checkboxes are updated only from remote-node evidence generated for the current commit.
