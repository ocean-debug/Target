# Disease–target–context relationship benchmark

This benchmark tests whether Target preserves the biological context around a
disease/target relation instead of collapsing it into an unconditional gene
ranking.

## What is included

- `disease_target_anchor`: every evidence-graded reference target already
  curated in `configs/disease_library.yaml`.
- `contextualized_target`: one representative target per disease under four
  conditions: complete context, missing cell type, swapped tissue and swapped
  disease stage.
- Context fields include organism, tissue, cell type, disease stage and desired
  phenotype.

The swapped cases are contrastive **benchmark-context mismatches**, not claims
that the relationship is biologically false. A correct Agent should flag or
degrade the mismatch and avoid a context-specific causal claim.

## Leakage controls

- Splits are disease-disjoint; every target and context variant for a disease
  stays in one split.
- A tissue/stage donor is selected only from another disease in the same split.
- No cross-disease target is used as a hard biological negative, because many
  targets are pleiotropic and such a label would be scientifically unsafe.
- Paper-level and time-based splitting should be added when each anchor has
  publication-level provenance; the current curated config does not contain
  enough source dates to make a defensible temporal split.

## Regenerate and validate

```bash
python benchmark/generate_context_relation_goldset.py
python benchmark/generate_context_relation_goldset.py --check
pytest tests/test_context_relation_benchmark.py
```

Predictions are JSONL rows with this minimal shape:

```json
{"id":"CR-...","label":"context_mismatch","actions":["flag_context_mismatch","avoid_context_specific_causal_claim"],"claims":[]}
```

Score them with:

```bash
python benchmark/evaluate_context_relations.py --predictions predictions.jsonl --output report.json
```

Reported rule-based metrics are coverage, label accuracy, required-action
recall and forbidden-claim safety, both overall and by task family.
