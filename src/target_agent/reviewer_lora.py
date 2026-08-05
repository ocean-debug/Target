"""Optional LoRA reviewer backend: a probe-based confirmation layer.

Design contract
---------------
The deterministic gates in reviewer.py are always authoritative; this backend
can only ADD findings, mirroring the Step LLM path. For every case condition
that matches one of the six review categories the adapter was trained on
(alignment_data/reviewer_sft.jsonl), a probe is fired with the exact SFT prompt
format; the structured {severity, category, action} answer is cross-checked
against the probe's expected category before it becomes a ReviewerFinding.
Answers that fail parsing or name the wrong category are discarded, so a
malfunctioning adapter degrades to silence rather than noise.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import EvidenceItem, ReviewerFinding, TaskSpec, ToolResult

PROMPT_TEMPLATE = (
    "Review this scientific-agent case and return structured JSON.\n"
    "Instruction: {instruction}\nInput: {payload}\nResponse:"
)

CATEGORIES = {
    "missing_context", "out_of_distribution", "conflicting_evidence",
    "causal_overreach", "tool_failure", "correct_refusal",
}
SEVERITIES = {"blocking", "major", "minor"}

# SFT taxonomy -> canonical ReviewerFinding.category (contract 2.2.0 Literal).
# The original SFT category stays visible in the finding message for traceability.
FINDING_CATEGORY_MAP = {
    "missing_context": "coverage_gap",
    "out_of_distribution": "context_mismatch",
    "conflicting_evidence": "conflicting_evidence",
    "causal_overreach": "causal_overreach",
    "tool_failure": "tool_failure",
    "correct_refusal": "coverage_gap",
}


def extract_json(text: str) -> dict | None:
    start = text.find("{")
    while start != -1:
        depth = 0
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:index + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def build_probes(task: TaskSpec, results: list[ToolResult],
                 evidence: list[EvidenceItem]) -> list[dict[str, Any]]:
    """One probe per concrete case condition, mirroring the SFT categories."""
    probes: list[dict[str, Any]] = []
    base_input: dict[str, Any] = {"contract_version": "2.2.0", "task_type": task.task_type}
    if task.task_type == "disease_to_target" and (not task.context.tissue or not task.context.cell_type):
        probes.append({
            "category": "missing_context",
            "instruction": "Prioritize a target, but tissue and cell type are missing.",
            "input": {**base_input, "disease": task.context.disease,
                      "tissue": task.context.tissue, "cell_type": task.context.cell_type},
            "related_ids": [task.task_id],
        })
    causal_words = ("causes", "causal evidence", "drives disease", "proves")
    for item in evidence:
        if item.claim_class.value != "INFERRED" and any(w in item.statement.lower() for w in causal_words):
            probes.append({
                "category": "causal_overreach",
                "instruction": "A differential-expression result is described as proof that the gene drives disease.",
                "input": {**base_input, "evidence_id": item.evidence_id, "claim_class": item.claim_class.value},
                "related_ids": [item.evidence_id],
            })
            break  # one representative probe per category is enough
    directions: dict[str, set] = {}
    ids_by_gene: dict[str, list] = {}
    for item in evidence:
        if item.gene_symbol and item.effect_direction in {"increase", "decrease"}:
            directions.setdefault(item.gene_symbol, set()).add(item.effect_direction)
            ids_by_gene.setdefault(item.gene_symbol, []).append(item.evidence_id)
    for gene, values in directions.items():
        if len(values) > 1:
            probes.append({
                "category": "conflicting_evidence",
                "instruction": "Two studies report opposite target directions in different cell states.",
                "input": {**base_input, "gene": gene, "directions": sorted(values)},
                "related_ids": ids_by_gene[gene][:10],
            })
            break
    for result in results:
        if result.status.value == "failed":
            probes.append({
                "category": "tool_failure",
                "instruction": f"{result.tool_name} timed out and no cache exists.",
                "input": {**base_input, "tool": result.tool_name, "status": result.status.value},
                "related_ids": [result.tool_run_id],
            })
        if result.status.value == "out_of_scope":
            probes.append({
                "category": "correct_refusal",
                "instruction": "Generate the cached MCH causal graph for an out-of-scope trait.",
                "input": {**base_input, "tool": result.tool_name,
                          "trait": result.inputs.get("trait")},
                "related_ids": [result.tool_run_id],
            })
        if result.context_match_score < 0.5 and result.outputs.get("formal_score_eligible") is not False:
            probes.append({
                "category": "out_of_distribution",
                "instruction": "Use an out-of-context model as formal evidence.",
                "input": {**base_input, "tool": result.tool_name,
                          "context_match_score": result.context_match_score},
                "related_ids": [result.tool_run_id],
            })
    return probes


class LoRAReviewerBackend:
    """Lazy-loading local LoRA reviewer; generates one structured answer per probe."""

    def __init__(self, base_path: Path, adapter_path: Path, max_new_tokens: int = 128):
        self.base_path = Path(base_path)
        self.adapter_path = Path(adapter_path)
        self.max_new_tokens = max_new_tokens
        self.name = f"lora:{self.adapter_path.name}"
        self._model = None
        self._tokenizer = None
        self._device = "cpu"

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(str(self.base_path), trust_remote_code=True)
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(str(self.base_path), torch_dtype="auto",
                                                     trust_remote_code=True)
        self._model = PeftModel.from_pretrained(model, str(self.adapter_path))
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(self._device)
        self._model.eval()

    def _answer(self, instruction: str, payload: dict) -> dict | None:
        import torch
        prompt = PROMPT_TEMPLATE.format(instruction=instruction,
                                        payload=json.dumps(payload, ensure_ascii=False))
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        with torch.no_grad():
            output = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens,
                                          do_sample=False, pad_token_id=self._tokenizer.pad_token_id)
        generation = self._tokenizer.decode(output[0][inputs["input_ids"].shape[1]:],
                                            skip_special_tokens=True)
        return extract_json(generation)

    def findings(self, task: TaskSpec, results: list[ToolResult],
                 evidence: list[EvidenceItem]) -> list[ReviewerFinding]:
        probes = build_probes(task, results, evidence)
        if not probes:
            return []
        self._load()
        findings: list[ReviewerFinding] = []
        for probe in probes[:8]:  # bounded adapter calls per case
            parsed = self._answer(probe["instruction"], probe["input"])
            if not parsed:
                continue
            severity = str(parsed.get("severity", "")).lower()
            category = str(parsed.get("category", ""))
            action = str(parsed.get("action", "")).strip()
            if severity not in SEVERITIES or category not in CATEGORIES or not action:
                continue
            if category != probe["category"]:
                continue  # adapter disagreed with the probe premise; discard silently
            canonical = FINDING_CATEGORY_MAP.get(category)
            if canonical is None:
                continue  # never emit a category outside the public contract
            findings.append(ReviewerFinding(
                severity=severity, category=canonical,
                message=f"LoRA reviewer confirmed {category}: {action}",
                related_ids=probe["related_ids"], required_action=action,
            ))
        return findings
