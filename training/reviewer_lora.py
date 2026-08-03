"""Review-gated LoRA entry point for the structured Reviewer backend.

This script never publishes or modifies runtime code. It refuses alignment rows
without both scientific and engineering approval unless an explicit local
development override is supplied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from target_agent.alignment import load_reviewed_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("alignment_data/reviewer_sft.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("models/reviewer-lora"))
    parser.add_argument("--model", default="Qwen/Qwen3-8B")
    parser.add_argument("--allow-pending-review", action="store_true", help="Smoke tests only; resulting adapter is not promotion eligible")
    parser.add_argument("--max-steps", type=int, default=100)
    args = parser.parse_args()

    rows = load_reviewed_rows(args.data, args.allow_pending_review)
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype="auto", device_map="auto", trust_remote_code=True)
    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    ))

    def tokenize(row: dict) -> dict:
        prompt = (
            "Review this scientific-agent case and return structured JSON.\n"
            f"Instruction: {row['instruction']}\nInput: {json.dumps(row['input'], ensure_ascii=False)}\nResponse:"
        )
        answer = json.dumps(row["response"], ensure_ascii=False)
        encoded = tokenizer(prompt + answer + tokenizer.eos_token, truncation=True, max_length=1024)
        encoded["labels"] = list(encoded["input_ids"])
        return encoded

    dataset = Dataset.from_list(rows).map(tokenize, remove_columns=list(rows[0]))
    training_args = TrainingArguments(
        output_dir=str(args.output), per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=2e-4, max_steps=args.max_steps, logging_steps=5, save_steps=args.max_steps,
        bf16=True, report_to="none", remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=dataset)
    trainer.train()
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    (args.output / "training_manifest.json").write_text(json.dumps({
        "base_model": args.model, "rows": len(rows), "max_steps": args.max_steps,
        "review_override": args.allow_pending_review,
        "promotion_eligible": not args.allow_pending_review,
        "runtime_role": "optional structured Reviewer backend; never controls the full Agent",
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
