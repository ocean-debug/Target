# TargetDiscovery Agent

A traceable life-science research Agent for disease-driven drug-target discovery. The product is an Agent; internal rubrics and tests are quality gates, not a standalone evaluation platform.

## What V2.1 does

```text
Disease -> GEO/CELLxGENE discovery -> metadata audit -> reviewed analysis recipe
        -> bulk/single-cell evidence -> pathways -> genetics/literature/drugs
        -> Reviewer -> ranking -> TargetCards -> traceable report
```

- Public contract `2.1.0` is defined by [contracts.py](src/target_agent/contracts.py); JSON Schemas are generated from Pydantic.
- GEO discovery uses NCBI E-Utils and official GEO HTTPS/FTP resources.
- PyDESeq2 accepts non-negative integer counts only. Continuous expression requires the explicitly enabled fixed limma backend.
- Standard H5AD and 10x formal DE requires donor, cell type and condition metadata and runs donor-by-cell-type-by-condition pseudobulk.
- CELLxGENE Census is a separately diagnosed optional backend fixed to version `2025-11-08`; an unavailable platform wheel is reported as a capability gap.
- UC snapshots, measured T-cell perturbation and DeltaFactor remain disabled compatibility plugins, not the default workflow.
- MCH/K562 remains an isolated causal-modelling gold sample.

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
target-agent serve --host 127.0.0.1 --port "$TARGET_AGENT_PORT"
```

`serve` uses Waitress. Add `--dev` only when the Flask development server is intentionally required.

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
