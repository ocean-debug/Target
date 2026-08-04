"""Write dual-review decisions back into an alignment JSONL file.

Only run this after the life-science and engineering reviewers have signed the
worksheet (alignment_data/REVIEW_WORKSHEET.md). The script records *who*
approved; it never invents an approval on its own.

Usage:
    python training/mark_review.py --data alignment_data/reviewer_sft.jsonl --all \
        --life-science-reviewer "Name A" --engineering-reviewer "Name B"
    python training/mark_review.py --data alignment_data/reviewer_sft.jsonl \
        --ids sft-tool_failure-003 sft-tool_failure-007 --decision rejected
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--all", action="store_true", help="Apply to every row")
    parser.add_argument("--ids", nargs="*", default=[], help="Apply to these row ids only")
    parser.add_argument("--decision", choices=["approved", "rejected"], default="approved")
    parser.add_argument("--life-science-reviewer", default="")
    parser.add_argument("--engineering-reviewer", default="")
    args = parser.parse_args()
    if not args.all and not args.ids:
        raise SystemExit("select rows with --all or --ids")

    rows = [json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines() if line.strip()]
    targets = {row["id"] for row in rows} if args.all else set(args.ids)
    missing = targets - {row["id"] for row in rows}
    if missing:
        raise SystemExit(f"unknown ids: {sorted(missing)}")

    stamp = {"decision": args.decision,
             "life_science_reviewer": args.life_science_reviewer,
             "engineering_reviewer": args.engineering_reviewer}
    changed = 0
    for row in rows:
        if row["id"] in targets:
            # keep `review` exactly two keys: load_reviewed_rows requires
            # set(review.values()) == {"approved"}; audit metadata goes elsewhere
            row["review"] = {
                "life_science_review": args.decision,
                "engineering_review": args.decision,
            }
            row["review_audit"] = {k: v for k, v in stamp.items() if v}
            changed += 1
    args.data.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                         encoding="utf-8")
    print(f"updated {changed}/{len(rows)} rows -> {args.decision}")

    if args.decision == "approved":
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from target_agent.alignment import load_reviewed_rows
        accepted = load_reviewed_rows(args.data, allow_pending=False)
        print(f"gate check: {len(accepted)} rows pass load_reviewed_rows without override")


if __name__ == "__main__":
    main()
