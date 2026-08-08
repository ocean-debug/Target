"""Pattern-few-shot ablation over the public disease gold set.

Offline mode (default) measures deterministic coverage: for every unique
disease in benchmark/goldset_diseases.jsonl (normal bucket) it builds the same
few-shot hints the Planner would receive, and verifies that the deterministic
plan stays valid. Live mode (--llm) additionally runs the Step planner with and
without pattern hints and compares plan shape; it costs real API calls and is
opt-in.

The report is an internal quality gate, never a claim that paper patterns
predict biological success.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from target_agent.legacy import parse_task_spec  # noqa: E402
from target_agent.paper_strategy import (  # noqa: E402
    PatternStore, PlannerFewShotBuilder, infer_data_availability,
)
from target_agent.paper_rag import PaperRagStore  # noqa: E402
from target_agent.planner import Planner  # noqa: E402
from target_agent.settings import load_settings  # noqa: E402
from target_agent.tools.base import ToolRegistry  # noqa: E402

from fakes import FakeGenericOmics, FakeLiterature, FakeOpenTargets  # noqa: E402


def load_goldset(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "-N-" in str(row.get("id", "")):
            rows.append(row)
    return rows


def _context(task: dict) -> dict:
    return task.get("context") or {}


def build_hint(store: PatternStore, task: dict) -> list[dict]:
    context = _context(task)
    availability = infer_data_availability(context)
    builder = PlannerFewShotBuilder(store, top_k=3)
    return builder.build(
        disease=str(context.get("disease") or task.get("question") or ""),
        tissue=context.get("tissue") if isinstance(context.get("tissue"), str) else None,
        cell_type=context.get("cell_type") if isinstance(context.get("cell_type"), str) else None,
        data_availability=availability,
    )


_RAG_LANE_TOKENS = {
    "genetics": ("gwas", "genetics", "genetic", "coloc", "eqtl", "locus", "variant"),
    "omics": ("omics", "expression", "transcriptom", "scrna", "single-cell", "single cell", "atac", "deseq", "geo", "bulk"),
    "single_cell": ("single-cell", "single cell", "scrna", "spatial", "cell type", "pseudobulk", "atlas"),
    "perturbation": ("perturb", "crispr", "knockout", "knockdown", "overexpress", "screen"),
    "drug": ("drug", "pharmacolog", "chembl", "inhibitor", "agonist", "antagonist"),
    "safety": ("safety", "toxicity", "adverse"),
    "trials": ("trial", "clinical"),
}


def _rag_lane_aligned(paper_lanes: list[str], step_names: list[str]) -> bool:
    """True when a RAG hit's inferred lanes appear in the deterministic plan."""
    hay = " ".join(step_names or ()).lower()
    for lane in paper_lanes:
        if any(token in hay for token in _RAG_LANE_TOKENS.get(lane, ())):
            return True
    return False


def offline(entries: list[dict], store: PatternStore, rag_store=None, paper_top_k: int = 2) -> dict:
    rows = []
    plan_failures = []
    rag_builder = None
    if rag_store is not None:
        rag_builder = PlannerFewShotBuilder(store=None, paper_rag=rag_store, paper_top_k=paper_top_k)
    for entry in entries:
        task_spec = parse_task_spec(entry["task"])
        hints = build_hint(store, entry["task"])
        try:
            registry = ToolRegistry([FakeGenericOmics(), FakeOpenTargets(), FakeLiterature()])
            plan = Planner(None, registry).create_plan(task_spec)
            plan_ok = True
            plan_detail = {
                "step_count": len(plan.steps),
                "step_ids": [step.step_id for step in plan.steps],
                "step_names": [step.name for step in plan.steps],
                "first_tool": next((step.tool for step in plan.steps if step.tool), None),
                "backend": plan.planner_backend,
            }
        except Exception as exc:
            plan_ok = False
            plan_detail = {"error": f"{exc.__class__.__name__}: {exc}"}
            plan_failures.append(entry["id"])
        paper_evidence: list[dict] = []
        if rag_builder is not None:
            paper_evidence = rag_builder.build_paper_evidence(
                disease=str(task_spec.context.disease or ""),
                tissue=task_spec.context.tissue if isinstance(task_spec.context.tissue, str) else None,
                cell_type=task_spec.context.cell_type if isinstance(task_spec.context.cell_type, str) else None,
                data_availability=infer_data_availability(context),
            )
        rows.append({
            "disease_id": task_spec.context.disease_id,
            "disease": task_spec.context.disease,
            "tissue": task_spec.context.tissue,
            "cell_type": task_spec.context.cell_type,
            "hint_count": len(hints),
            "pattern_ids": [hint["pattern_id"] for hint in hints],
            "rag_hit_count": len(paper_evidence),
            "rag_papers": sorted({str(item.get("pmid") or "") for item in paper_evidence})[:10],
            "rag_lanes": sorted({lane for item in paper_evidence for lane in (item.get("lane_tags") or [])}),
            "rag_lane_aligned": _rag_lane_aligned(
                sorted({lane for item in paper_evidence for lane in (item.get("lane_tags") or [])}),
                plan_detail.get("step_names", []),
            ) if paper_evidence else False,
            "plan_ok": plan_ok,
            "plan": plan_detail,
        })
    hit_rows = [row for row in rows if row["hint_count"] > 0]
    rag_rows = [row for row in rows if row["rag_hit_count"] > 0]
    top_patterns = Counter(
        pattern_id for row in rows for pattern_id in row["pattern_ids"]
    ).most_common(10)
    return {
        "mode": "offline",
        "diseases_total": len(rows),
        "diseases_with_hints": len(hit_rows),
        "coverage": round(len(hit_rows) / len(rows), 4) if rows else 0.0,
        "avg_hints": round(sum(row["hint_count"] for row in rows) / len(rows), 3) if rows else 0.0,
        "plan_valid": sum(1 for row in rows if row["plan_ok"]),
        "plan_failures": plan_failures,
        "top_patterns": [{"pattern_id": pid, "diseases": count} for pid, count in top_patterns],
        "rag": {
            "enabled": rag_store is not None,
            "diseases_with_rag_hits": len(rag_rows),
            "rag_coverage": round(len(rag_rows) / len(rows), 4) if rows else 0.0,
            "avg_rag_hits": round(
                sum(row["rag_hit_count"] for row in rows) / len(rows), 3,
            ) if rows else 0.0,
            "lane_aligned_diseases": sum(1 for row in rows if row["rag_lane_aligned"]),
        },
        "diseases": rows,
    }


def live(entries: list[dict], store: PatternStore, settings, limit: int) -> dict:
    from target_agent.llm import StepClient

    client = StepClient.from_settings(settings)
    if client is None:
        raise SystemExit("Step API is not configured; --llm requires a configured provider")
    registry = ToolRegistry([FakeGenericOmics(), FakeOpenTargets(), FakeLiterature()])
    baseline_planner = Planner(client, registry, pattern_store=None)
    enhanced_planner = Planner(client, registry, pattern_store=store)
    comparisons = []
    for entry in entries[: max(0, limit)]:
        task_spec = parse_task_spec(entry["task"])
        baseline = baseline_planner.create_plan(task_spec)
        enhanced = enhanced_planner.create_plan(task_spec)
        comparisons.append({
            "disease_id": task_spec.context.disease_id,
            "disease": task_spec.context.disease,
            "baseline": {
                "backend": baseline.planner_backend,
                "step_count": len(baseline.steps),
                "step_ids": [step.step_id for step in baseline.steps],
            },
            "enhanced": {
                "backend": enhanced.planner_backend,
                "step_count": len(enhanced.steps),
                "step_ids": [step.step_id for step in enhanced.steps],
                "hint_count": len(getattr(enhanced_planner, "last_pattern_hints", []) or []),
                "pattern_ids": [hint.get("pattern_id") for hint in (enhanced_planner.last_pattern_hints or [])],
            },
            "shape_changed": [step.step_id for step in baseline.steps] != [step.step_id for step in enhanced.steps],
            "review_preserved": any(step.step_id == "review" for step in enhanced.steps),
        })
    return {
        "mode": "live",
        "compared": len(comparisons),
        "hints_used": sum(1 for row in comparisons if row["enhanced"]["hint_count"] > 0),
        "shape_changed": sum(1 for row in comparisons if row["shape_changed"]),
        "review_preserved": all(row["review_preserved"] for row in comparisons),
        "comparisons": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goldset", type=Path, default=ROOT / "benchmark" / "goldset_diseases.jsonl")
    parser.add_argument("--store", type=Path, default=ROOT / "paper_strategy" / "patterns.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmark" / "reports")
    parser.add_argument("--llm", action="store_true", help="also compare real Step planner output (opt-in, costs API calls)")
    parser.add_argument("--limit", type=int, default=0, help="live mode: cap compared diseases (0 = all)")
    parser.add_argument("--rag", type=Path, default=None, help="paper RAG store (chunks.jsonl) for coverage analysis")
    parser.add_argument("--paper-top-k", type=int, default=2, help="paper RAG hits per disease")
    args = parser.parse_args()

    entries = load_goldset(args.goldset)
    store = PatternStore(args.store)
    report: dict = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    rag_store = None
    if args.rag is not None and args.rag.is_file():
        rag_store = PaperRagStore(args.rag)
    report["offline"] = offline(entries, store, rag_store=rag_store, paper_top_k=args.paper_top_k)
    if args.llm:
        report["live"] = live(entries, store, load_settings(), args.limit)

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    json_path = args.out / f"pattern_ablation_{stamp}.json"
    md_path = args.out / f"pattern_ablation_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    offline_report = report["offline"]
    lines = [
        "# Pattern Few-shot Ablation Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Store: {args.store.name}",
        f"- Mode: offline{' + live' if args.llm else ''}",
        "",
        "## Offline coverage",
        "",
        f"- Diseases considered: {offline_report['diseases_total']}",
        f"- Diseases with at least one pattern hint: {offline_report['diseases_with_hints']}",
        f"- Coverage: {offline_report['coverage'] * 100:.1f}%",
        f"- Average hints per disease: {offline_report['avg_hints']}",
        f"- Deterministic plans valid: {offline_report['plan_valid']}/{offline_report['diseases_total']}",
        "",
    ]
    rag_report = offline_report.get("rag") or {}
    if rag_report.get("enabled"):
        lines += [
            "## Paper-RAG coverage (strategy hints, not evidence)",
            "",
            f"- Diseases with RAG hits: {rag_report['diseases_with_rag_hits']}",
            f"- RAG coverage: {rag_report['rag_coverage'] * 100:.1f}%",
            f"- Average RAG hits per disease: {rag_report['avg_rag_hits']}",
            f"- Diseases whose RAG lanes align with the plan: {rag_report['lane_aligned_diseases']}",
            "",
        ]
    lines += [
        "### Top patterns",
        "",
        "| Pattern | Diseases hit |",
        "|---|---|",
    ]
    for row in offline_report["top_patterns"]:
        lines.append(f"| {row['pattern_id']} | {row['diseases']} |")
    if offline_report["plan_failures"]:
        lines += ["", "### Plan failures", ""]
        lines.extend(f"- {failure}" for failure in offline_report["plan_failures"])
    lines += ["", "### Per-disease hints", "", "| Disease | Tissue | Cell type | Hints | Patterns | RAG hits | RAG aligned |", "|---|---|---|---|---|---|---|"]
    for row in offline_report["diseases"]:
        lines.append(
            f"| {row['disease']} | {row['tissue'] or '-'} | {row['cell_type'] or '-'} | "
            f"{row['hint_count']} | {', '.join(row['pattern_ids']) or '-'} | "
            f"{row.get('rag_hit_count', 0)} | {'yes' if row.get('rag_lane_aligned') else 'no'} |"
        )
    if args.llm:
        live_report = report["live"]
        lines += [
            "",
            "## Live planner comparison",
            "",
            f"- Compared: {live_report['compared']}",
            f"- Runs where hints were used: {live_report['hints_used']}",
            f"- Plan shape changed: {live_report['shape_changed']}",
            f"- Review step preserved: {live_report['review_preserved']}",
            "",
            "| Disease | Baseline steps | Enhanced steps | Hint count | Shape changed |",
            "|---|---|---|---|---|",
        ]
        for row in live_report["comparisons"]:
            lines.append(
                f"| {row['disease']} | {row['baseline']['step_count']} | {row['enhanced']['step_count']} | "
                f"{row['enhanced']['hint_count']} | {row['shape_changed']} |"
            )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "mode": report["offline"]["mode"],
        "diseases_total": report["offline"]["diseases_total"],
        "diseases_with_hints": report["offline"]["diseases_with_hints"],
        "coverage": report["offline"]["coverage"],
        "plan_valid": report["offline"]["plan_valid"],
        "rag_enabled": bool((report["offline"].get("rag") or {}).get("enabled")),
        "rag_coverage": (report["offline"].get("rag") or {}).get("rag_coverage"),
        "report_json": str(json_path),
        "report_md": str(md_path),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
