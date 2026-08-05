# TargetDiscovery Agent

A traceable, recoverable vertical Agent for disease-driven drug-target discovery. It connects genetics, disease-context omics, perturbation, mechanism, druggability and safety evidence into ranked candidates, TargetCards and falsifiable experiments. Internal rubrics and benchmarks are quality gates, not the product itself.

V3 adds an internal project-level reliability layer above the validated V2.1 target-discovery runtime: typed work items, immutable artifacts, resumable execution, append-only decisions and independent review. This infrastructure does not turn Target into a general-purpose scientific workbench. See [PRODUCT_V3.md](docs/PRODUCT_V3.md) for the product boundary, current capability and roadmap.

## Validated target-discovery workflow (V2.1)

## What V2.1 does

```text
Disease -> GEO/CELLxGENE discovery -> metadata audit -> reviewed analysis recipe
        -> bulk/single-cell evidence -> pathways -> genetics/literature/drugs/trials
        -> Reviewer -> ranking -> TargetCards -> traceable report
```

- Public contract `2.1.0` is defined by [contracts.py](src/target_agent/contracts.py); JSON Schemas are generated from Pydantic.
- GEO discovery uses NCBI E-Utils and official GEO HTTPS/FTP resources.
- ClinicalTrials.gov API v2 adds gene-named trial-registry evidence (`clinical_trials_gov`); claims are emitted only when the intervention or title text explicitly names the gene, and stopped trials are downgraded to uncertain.
- The literature tool upgrades to full-text-aware RAG: open-access PMC full texts are section-parsed into a persistent shared FTS5 corpus with optional LLM reranking and bm25 fallback.
- Two execution engines ship and are parity-tested: the legacy hand-rolled state machine and the LangGraph `StateGraph` runtime (default; `--runtime legacy` opts out). Both write byte-compatible run artifacts and share the same checkpoint/resume contract.
- A systematic benchmark lives in [benchmark/](benchmark/): 14 gold tasks (fake/unit/live modes) covering the main chain, robustness, determinism, recovery, contract gates and engine parity; `python benchmark/runner.py` must score 100% in fake+unit mode.
- The Reviewer LoRA pipeline (data + training + heldout evaluation + remote GPU runbook) is under [training/](training/); local CPU smoke is verified, full training runs on the external GPU profile only. At runtime the trained adapter acts as an optional probe-based confirmation layer inside the Reviewer (configure `TARGET_AGENT_REVIEWER_LORA_BASE`/`TARGET_AGENT_REVIEWER_LORA_ADAPTER`): deterministic gates stay authoritative, adapter answers are category-cross-checked and silently discarded on any parse/category failure, and SFT categories are mapped onto the canonical finding taxonomy before a ReviewerFinding is emitted.
- PyDESeq2 accepts non-negative integer counts only. Continuous expression requires the explicitly enabled fixed limma backend.
- Standard H5AD and 10x formal DE requires donor, cell type and condition metadata and runs donor-by-cell-type-by-condition pseudobulk.
- CELLxGENE Census is a separately diagnosed optional backend fixed to version `2025-11-08`; an unavailable platform wheel is reported as a capability gap.
- UC snapshots, measured T-cell perturbation and DeltaFactor remain disabled compatibility plugins, not the default workflow.
- MCH/K562 remains an isolated causal-modelling gold sample.

## Disease library

[configs/disease_library.yaml](configs/disease_library.yaml) is the curated disease library behind [diseases.py](src/target_agent/diseases.py):

- 18 diseases across autoimmune, neurodegenerative, cancer, metabolic and respiratory categories. Every `ontology_id` (MONDO/EFO) was verified against live EBI OLS search on 2026-08-04; new identifiers must pass the same live check before being added.
- Each entry carries evidence-graded reference targets (`approved_drug > gwas > mendelian > clinical_trial > mechanistic`) used as ranking sanity anchors, plus a default biological context (tissue / cell type / stage / desired phenotype).
- Four benchmark task templates follow the project 50/20/15/15 composition: `normal`, `missing_context` (blanks tissue/cell type), `conflicting_evidence` and `trap` (causal-overreach provocation), each with a machine-checkable `expectation` block for the benchmark layer.
- The disease resolver merges library aliases at runtime, so every id, English name, Chinese name and synonym resolves to the verified ontology identifier without touching the OLS network path.

```bash
target-agent diseases                                  # list the library
target-agent run-disease --disease uc,ra,ad            # batch-run library diseases
target-agent run-disease --disease uc --kind missing_context --summary-out batch.json
```

The same four buckets feed the benchmark: `benchmark/generate_disease_goldset.py` renders
`goldset_diseases.jsonl` (72 fake-mode entries, CI gate at 100%) and `goldset_diseases_lora.jsonl`
(live matrix whose expectation-derived assertions require the Reviewer LoRA backend).

The regression matrices do not measure biological ranking quality. A separate scorer-only blind
ranking protocol is documented in [benchmark/rubric.md](benchmark/rubric.md): Agent task, ranking
and terminal-status artifacts are digest-frozen before a Git-external private label file is opened,
then scored with
disease-macro nDCG/Recall/MRR and independent trap/safety gates. The scorer is implemented; an
external expert-adjudicated final label set, evaluator-controlled scorer and publishable blind
performance result are not yet available.

## Install

Python 3.11 is the acceptance runtime.

```bash
python -m pip install -e ".[test,omics-bulk,omics-single-cell]"
# Optional only when the deployment platform supports its TileDB-SOMA wheel:
python -m pip install -e ".[omics-census]"
target-agent doctor
```

Copy `.env.example` to an untracked `.env`, or inject variables through the process environment. Process variables override dotenv values. Never commit a real key.

```bash
target-agent --env-file .env llm-smoke-test
target-agent run --input cases/main_demo/input.uc_demo.yaml
target-agent project-run --input cases/research_project.example.yaml
target-agent project-status --project-id project-alzheimer-example
# For the example's checkpointed mode, accept the printed plan id and resume:
target-agent project-approve --project-id project-alzheimer-example --target-id PLAN_ID \
  --actor reviewer --rationale "Plan scope and evidence budget accepted" --resume
target-agent serve --host 127.0.0.1 --port "$TARGET_AGENT_PORT"
```

`serve` uses Waitress. Add `--dev` only when the Flask development server is intentionally required.
The V3 HTTP surface adds `POST /api/projects`, `GET /api/projects/{project_id}`,
`GET /api/projects/{project_id}/events`, `POST /api/projects/{project_id}/decisions` and
content-addressed artifact downloads. `checkpointed` projects require plan and release acceptance;
`supervised` projects additionally require each work-item acceptance. MCP publication remains a roadmap integration.

## Demo workbench

The workbench supports two paths without changing the scientific runtime:

- **Validated replay:** `/api/demo/cases` lists available curated runs, and `/api/runs/{run_id}/bundle` returns a frontend-ready, secret-safe view of the stored Plan, Trace, tools, evidence, ranking, TargetCards and Reviewer findings.
- **Live run:** the same page submits a new `TaskSpec 2.1.0`, streams Trace events over SSE and renders the resulting backend artifacts when the run reaches a terminal state.

Replay is explicitly labelled as a validated stored run. It does not call Step or public databases and is the recommended five-minute presentation path. Live execution remains available when network time permits.

See [DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for the five-minute narration, verification checklist and recovery path.

## Deployment portability

The repository contains no SSH target, remote path, Conda environment, scheduler queue, node, core count, GPU selection or service tunnel. Those values belong in an external deployment profile. Missing resource fields must fail rather than be guessed. See [REMOTE_ACCEPTANCE.md](docs/REMOTE_ACCEPTANCE.md).

## Scientific boundaries

- `FACT`, `OBSERVED`, `PREDICTED` and `INFERRED` are never conflated.
- Search hits are not evidence until an exact source span or reproducible analysis output exists.
- Low-context predictions are excluded from formal ranking.
- Missing public omics data degrades to `completed_with_gaps`; genetics, literature and drug evidence continue.
- Reports and the UI render structured Evidence Store values only.
- Every analyzed source is bound to a checksum; analysis caches also bind the recipe, tool version, biological context and contract version.
- Raw FASTQ/SRA, arbitrary GEO layouts, spatial analysis, patents and automatic code/training mutation are outside V2.1.

## Repository policy

Run all project tests and builds in the user-supplied remote execution profile. Large data, caches, models, `.env` files and deployment profiles stay outside Git.
