# V2.1 historical baseline and V2.2 acceptance report

This file records portable acceptance facts only. Infrastructure identifiers are retained in the external execution profile and private job logs.

The V2.1 checks and evidence below are a historical baseline; they do not by themselves validate the current V2.2 branch. Current-commit V2.2 evidence is recorded in a separate section after remote acceptance.

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
- [x] Internal contract/regression benchmark: 14 tasks, fake+unit modes score 100% (27/27 assertions). This is not an external blind biological result.
- [x] Reviewer LoRA: data gates enforced, CPU smoke train/save/load/evaluate verified, remote GPU runbook documented.

## Latest portable evidence

- 33 remote-node tests passed, including unfinished-run identity recovery, stable checksum-bound cache keys, one bounded structured-output repair, request-ID capture, generic Planner routing, non-integer DESeq rejection and donor-level pseudobulk execution.
- Repository policy scan passed and all 16 generated JSON Schemas contain contract `2.1.0` only.
- Alignment factory produced 120 SFT rows, 60 preference pairs and 30 held-out acceptance rows with role-based review gates. The 120 SFT rows represent six reviewed templates with 20 indexed variants each; they are not 120 independent target-research cases.
- Live cold-search probes discovered disease-specific GEO candidates for Alzheimer disease and lung adenocarcinoma without an accession in TaskSpec.
- GSE318560 completed an Alzheimer-disease PyDESeq2 run; GSE104854 completed the independent lung-adenocarcinoma gold-input PyDESeq2 run.
- Alzheimer disease selected GSE248417/GSE318560 dynamically: cold run 47 seconds; cached runs 20, 7 and 5 seconds with identical status and rankings.
- Lung adenocarcinoma selected GSE310170 dynamically: cold run 79 seconds; cached runs 19, 8 and 8 seconds with identical status and rankings.
- UC selected GSE177044 dynamically but had no eligible automatic bulk result, so it correctly returned `completed_with_gaps`; cached runs took 7, 7 and 6 seconds with identical status and rankings.
- A scheduled-node Waitress process passed live `/healthz` and `/api/capabilities` checks using the externally supplied loopback bind and service port; the process was stopped after acceptance.
- A real Step 3.7 Flash smoke test produced a valid 14-step plan without fallback in 23.0 seconds; the provider request ID was captured without exposing the API key.
- Historical workstation diagnostic after V2.1 (not a release acceptance): 45 tests passed and 2 skipped; `python benchmark/runner.py` scored 27/27 assertions across 11 executed tasks (3 live tasks recorded separately); a live ClinicalTrials.gov probe returned 12 gene-named evidence items for EGFR/KRAS in lung adenocarcinoma; the LangGraph engine matched the legacy engine on ranking, evidence, findings, tool results and trace topology; the Reviewer LoRA CPU smoke (Qwen3-0.6B, 1 step) wrote a loadable adapter and the heldout evaluator parsed every generation as valid JSON.
- Reviewer LoRA full training completed on the external GPU profile (single H100, Qwen3-8B, 100 steps, ~2.5 min, train_loss 0.57). Heldout acceptance (30 rows, per training/RUNBOOK.md gates): base model json_valid 0.933 / category_match 0.0 / fully_correct 0.0; adapter json_valid 1.0 / category_match 1.0 / fully_correct 1.0. The adapter beat the base model on this 30-row template-consistent contract heldout set; this does not establish open-world Reviewer quality. Role-gate review was recorded by one project owner acting in both scientific and engineering roles, so it is not a two-person independent review or expert panel. The promotion run trained without `--allow-pending-review`, so the manifest records `promotion_eligible: true`. Model weights and evaluation outputs were external, Git-excluded acceptance artifacts under `models/reviewer-lora/`.
- Disease library (2026-08-04): 18 curated diseases in configs/disease_library.yaml; every ontology identifier (MONDO/EFO) passed a live EBI OLS exact-label verification on 2026-08-04. Reference targets are evidence-graded and machine-checked by tests (unique ids, CURIE format, >=2 graded targets per entry). Four task templates encode the 50/20/15/15 composition (normal / missing_context / conflicting_evidence / trap) with machine-checkable expectations. `target-agent diseases`, `target-agent run-disease` and `/api/diseases` expose the library; the disease resolver merges library aliases at runtime. Local regression: 59 passed, 2 skipped.
- Reviewer LoRA live end-to-end (2026-08-04, external GPU profile): `target-agent run-disease --disease uc` with the trained adapter configured completed the full live pipeline (12 tool calls, terminal `completed_with_gaps`; archived at runs_archive/run-lora-e2e3-uc/). Trace records `reviewer_backend: lora:reviewer-lora` and the adapter emitted a confirmed finding (`major/context_mismatch`, "LoRA reviewer confirmed out_of_distribution"). Two earlier attempts exposed real defects that are now fixed and regression-tested: GPU OOM degradation (all node GPUs occupied by other tenants; reviewer ran on CPU) and a category-mapping bug where confirmed SFT-only categories (missing_context/out_of_distribution/correct_refusal) crashed ReviewerFinding construction and silently degraded to `deterministic:lora_unavailable`; SFT categories are now mapped onto the canonical taxonomy via FINDING_CATEGORY_MAP. The graceful degradation itself behaved as designed: both degraded runs still completed with the deterministic reviewer.
- Disease-library benchmark goldsets (2026-08-04): benchmark/generate_disease_goldset.py renders 72 fake entries (18 diseases x 4 buckets) scoring 234/234 assertions = 1.0 across all four buckets, and 72 live LoRA entries; the main goldset still scores 27/27 = 1.0. These cases validate contract behavior, refusal and recovery of known reference anchors; they are not a blind target-discovery accuracy result.
- Live disease-library matrix (2026-08-04, external GPU profile, LoRA reviewer configured; artifacts in runs_archive/): Alzheimer disease `completed_with_gaps` (top-3 PSEN1/APP/PSEN2, reviewer_backend lora:reviewer-lora); UC missing_context bucket `completed_with_gaps` with the adapter confirming `missing_context` (canonical coverage_gap) — the exact assertion encoded in goldset_diseases_lora.jsonl; UC trap bucket `completed_with_gaps` with ZERO causal FACT/OBSERVED claims despite the causal-provocation question (top-3 unchanged IL12B/IL23R/IL10); first LUAD attempt hit transient GEO/Open Targets network failures and degraded to `completed_with_gaps` with the adapter confirming `tool_failure` (evidence marked missing, nothing fabricated); the LUAD rerun completed the full pipeline with 10 ranked targets (top-3 EGFR/TP63/NRG1, EGFR being a library approved-drug reference anchor) and `reviewer_backend: lora:reviewer-lora`.
- Full live disease-library matrix (2026-08-04/05, external profile, 4-way sharded runner with `--shared-cache` and per-entry crash isolation, LoRA reviewer on CPU): all 72 entries (18 diseases x 4 buckets) executed live against benchmark/goldset_diseases_lora.jsonl with final score 72/72 tasks and 270/270 assertions = 1.0, zero crashes. Per-bucket assertion scores: normal 72/72, missing_context 72/72 (adapter confirmed the planted coverage gap in every bucket entry), conflicting_evidence 54/54, trap 72/72 (zero causal overreach). Normal-bucket top genes recovered literature-consistent anchors across all five disease categories (UC/Crohn/psoriasis→IL12B, RA→CD40, SLE→TYK2, MS→CD58, T1D→SH2B3, AD→PSEN1, PD→PRKN, ALS→FUS, LUAD→EGFR, BRCA→BRIP1, CRC→TP53, melanoma→BRAF, T2D→GCK, NASH→PNPLA3, asthma→IL13, COPD→CHRNA3). Every run terminated `completed`/`completed_with_gaps` (designed degradation, nothing fabricated). This is a contract/reliability matrix with known anchors, not external blind biological validation. Artifacts were retained outside Git under the acceptance run archive.

## Current environment-specific gaps

- The validated node exposes Scanpy 1.11.5 and AnnData 0.12.16. Its operating-system ABI has no compatible TileDB-SOMA wheel required by `cellxgene-census==1.17.*`, so Census is correctly reported unavailable rather than silently downgraded.
- The optional fixed limma backend is not declared ready because neither Rscript nor the limma package is present.
- The historical Reviewer adapter was promotion-eligible under the then-current two-role gate with no training override. Both roles were completed by one owner, so this is not independent dual-person review. If team policy requires two reviewers, record separate role identities outside public artifacts, re-run `training/mark_review.py`, and retrain per `training/RUNBOOK.md` §3.

The checkboxes above record the historical V2.1 remote-node baseline, not current V2.2 acceptance.

## V3 project-control-plane acceptance (2026-08-05)

- Full remote pytest suite passed; two pre-existing model-dependent cases were skipped by their declared capability gates.
- The internal V2.1 benchmark remained at 11/11 tasks and 27/27 assertions after adding the project control plane.
- Bounded Reviewer repair was exercised against a transient Europe PMC connector failure: the runtime retried the allowlisted read-only tool, appended both attempts to the evidence ledger, emitted replan/re-review trace events and removed the recovered `tool_failure` from the final findings. Cache-only execution correctly performed no retry.
- Reviewer repair remains deliberately narrow: it cannot execute arbitrary code or mutate scientific methods, and it stops at the configured review-round and tool-call budgets.
- A real Step 3.7 Flash request produced the protected four-item vertical plan whose labels included project brief, target discovery, independent review and report. This validates plan structure only; it does not prove model- or expert-independent scientific review.
- The checkpointed smoke project stopped at `needs_input` before any scientific module ran and recorded the exact plan identifier requiring human acceptance.
- Canonical Pydantic export produced 11 new research-project JSON Schemas under `schemas/`.
- Repository policy scan returned `REPO_POLICY=OK` after generated runtime outputs were kept under excluded artifact storage.
- Acceptance covered atomic project reservation, cross-process execution locking, terminal-resume integrity checks, protected planner contracts, input/output alignment gates, dependency failure, attempt budget, content-addressed artifact versions, fail-closed target deliverables and plan/release checkpoints.

## Internal blind-ranking scorer protocol acceptance — no external biological result (2026-08-05)

- The full remote test suite passed after adding the scorer contracts; two pre-existing model-dependent cases remained skipped by their declared capability gates.
- Existing regression quality gates remained at 11/11 tasks and 27/27 assertions, and repository policy returned `REPO_POLICY=OK`.
- The reference scorer freezes `task_spec.json`, `ranked_targets.json` and terminal `status.json` with individual and combined SHA-256 digests before private labels are loaded.
- Tests cover graded nDCG/Recall/MRR, non-compensating trap and safety gates, candidate-label leakage, post-freeze ranking tampering, duplicate predictions, empty rankings, malformed-case isolation, explicit suite thresholds and expert-label schema/gate logic using development fixtures.
- Public score output is aggregate-only; per-case label signals are available only through an explicit organizer-audit path.
- Two canonical JSON Schemas were exported for the public manifest and private-label contracts.
- This acceptance validates the protocol and participant-side reference implementation only. It is not an external blind biological result; evaluator-controlled code, hidden diseases, expert labels and submission controls are still required.
