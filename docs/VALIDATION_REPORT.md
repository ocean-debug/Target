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
- [x] ClinicalTrials.gov evidence tool: gene-name-gated claims, stopped-trial downgrade, cache-only degradation.
- [x] Literature RAG upgrade: PMC full-text sections in a persistent shared FTS5 corpus; LLM reranking falls back to bm25.
- [x] LangGraph runtime parity: identical observable output, budget degradation, terminal and mid-pipeline resume vs the legacy engine.
- [x] Systematic benchmark: 14 gold tasks, fake+unit modes score 100% (27/27 assertions).
- [x] Reviewer LoRA: data gates enforced, CPU smoke train/save/load/evaluate verified, remote GPU runbook documented.

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
- Post-V2.1 additions (validated locally on the acceptance workstation): 45 tests passed and 2 skipped; `python benchmark/runner.py` scored 27/27 assertions across 11 executed tasks (3 live tasks recorded separately); a live ClinicalTrials.gov probe returned 12 gene-named evidence items for EGFR/KRAS in lung adenocarcinoma; the LangGraph engine matched the legacy engine on ranking, evidence, findings, tool results and trace topology; the Reviewer LoRA CPU smoke (Qwen3-0.6B, 1 step) wrote a loadable adapter and the heldout evaluator parsed every generation as valid JSON.
- Reviewer LoRA full training completed on the external GPU profile (single H100, Qwen3-8B, 100 steps, ~2.5 min, train_loss 0.57). Heldout acceptance (30 rows, per training/RUNBOOK.md gates): base model json_valid 0.933 / category_match 0.0 / fully_correct 0.0; adapter json_valid 1.0 / category_match 1.0 / fully_correct 1.0. The adapter beats the base model on every rubric dimension. SFT dual review was signed by the project owner against alignment_data/REVIEW_WORKSHEET.md and written back with training/mark_review.py (audit metadata in `review_audit`); the promotion run trained WITHOUT `--allow-pending-review`, so the manifest records `promotion_eligible: true`. The heldout rows are template-consistent with the SFT distribution, so the perfect score validates the output contract, not yet open-world reviewer judgement. Artifacts: models/reviewer-lora/ (adapter + eval_base/eval_adapter reports).
- Disease library (2026-08-04): 18 curated diseases in configs/disease_library.yaml; every ontology identifier (MONDO/EFO) passed a live EBI OLS exact-label verification on 2026-08-04. Reference targets are evidence-graded and machine-checked by tests (unique ids, CURIE format, >=2 graded targets per entry). Four task templates encode the 50/20/15/15 composition (normal / missing_context / conflicting_evidence / trap) with machine-checkable expectations. `target-agent diseases`, `target-agent run-disease` and `/api/diseases` expose the library; the disease resolver merges library aliases at runtime. Local regression: 59 passed, 2 skipped.
- Reviewer LoRA live end-to-end (2026-08-04, external GPU profile): `target-agent run-disease --disease uc` with the trained adapter configured completed the full live pipeline (12 tool calls, terminal `completed_with_gaps`; archived at runs_archive/run-lora-e2e3-uc/). Trace records `reviewer_backend: lora:reviewer-lora` and the adapter emitted a confirmed finding (`major/context_mismatch`, "LoRA reviewer confirmed out_of_distribution"). Two earlier attempts exposed real defects that are now fixed and regression-tested: GPU OOM degradation (all node GPUs occupied by other tenants; reviewer ran on CPU) and a category-mapping bug where confirmed SFT-only categories (missing_context/out_of_distribution/correct_refusal) crashed ReviewerFinding construction and silently degraded to `deterministic:lora_unavailable`; SFT categories are now mapped onto the canonical taxonomy via FINDING_CATEGORY_MAP. The graceful degradation itself behaved as designed: both degraded runs still completed with the deterministic reviewer.

## Current environment-specific gaps

- The validated node exposes Scanpy 1.11.5 and AnnData 0.12.16. Its operating-system ABI has no compatible TileDB-SOMA wheel required by `cellxgene-census==1.17.*`, so Census is correctly reported unavailable rather than silently downgraded.
- The optional fixed limma backend is not declared ready because neither Rscript nor the limma package is present.
- The trained Reviewer adapter is promotion-eligible at the pipeline level (dual review signed by the owner; no training override). If a second independent reviewer is required by team policy, co-sign alignment_data/REVIEW_WORKSHEET.md and re-run training/mark_review.py with both names, then retrain per training/RUNBOOK.md §3.

The checkboxes are updated only from remote-node evidence generated for the current commit.
