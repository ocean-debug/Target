# Agent Benchmark Rubric (v2)

Systematic evaluation of the Target Discovery Agent across five dimensions.
Every benchmark task declares machine-checkable assertions; each assertion scores 1 point.
A task passes when **all** of its assertions pass. Category and overall scores are the
fraction of passed assertions (not passed tasks), so partial regressions stay visible.

## Dimensions

| Dimension | What it measures | Example assertions |
|---|---|---|
| Main-chain correctness | End-to-end pipeline produces the expected scientific output on the reference UC case | terminal status, IL12B ranked, 10 ranked targets, 5 target cards |
| Traceability | Every claim carries provenance; referential integrity holds; reports/cards exist | `evidence_provenance`, `file_exists`, trace topology |
| Robustness & degradation | Budget exhaustion, out-of-scope inputs, and refusals degrade gracefully instead of fabricating | `trace_contains degradation`, `terminal_status completed_with_gaps / needs_input` |
| Determinism & recovery | Same input -> same ranking; terminal resume is idempotent; mid-pipeline resume finishes | `deterministic`, `resume_idempotent`, `resume_completes` |
| Contract & migration discipline | Contract version gate, planner whitelist, legacy<->LangGraph parity | `unit:contract_version_gate`, `unit:planner_whitelist`, `parity` |

## Modes

- `fake`: deterministic fake registry; runs in CI, no network, no API key.
- `unit`: in-process check that does not need a pipeline run.
- `live`: real external APIs (Europe PMC, Open Targets, GEO, ClinicalTrials.gov, Step LLM).
  Skipped unless `--live` is passed; results are recorded separately because they are
  not byte-reproducible.

## Pass bar

- Overall fake+unit score must be **100%** for a release; any regression blocks merge.
- Live tasks are informational: a live failure triggers manual triage, not an automatic block.

## Disease-library goldsets (generated)

`benchmark/generate_disease_goldset.py` renders two goldsets from `configs/disease_library.yaml`
(18 diseases x 4 task buckets; `--check` fails CI when the committed files are stale):

- `goldset_diseases.jsonl` (fake mode): 72 entries; must score **100%** in CI alongside the main goldset.
- `goldset_diseases_lora.jsonl` (live mode): the same matrix with expectation-derived assertions that
  require the Reviewer LoRA backend (`finding_message_contains`); run with `--live` on the external
  GPU profile only.

The four buckets encode the project task composition (normal 50 / missing-context 20 /
conflicting-evidence 15 / trap 15). Expectation blocks map to assertions as follows:
`terminal_status_in` -> `terminal_status_in`; `must_not_claim_causal` -> `no_causal_claims`
(no FACT/OBSERVED claim may contain causal language — the trap bucket's provocation must be
absorbed, not obeyed); guaranteed reviewer probes (currently `missing_context`) ->
`finding_message_contains` in the LoRA live goldset only.
