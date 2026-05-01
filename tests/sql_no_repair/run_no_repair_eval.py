"""SQL Harness ablation with retry and repair disabled.

This script uses the existing SQL Harness prompt and validation path, but fixes
max_retries to 0. It measures the contribution of the repair loop by comparing
its results against tests/sql_test/run_sql_chain_eval.py with retries enabled.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.sql_test.run_sql_chain_eval import (
    Text2SQLAgent,
    build_summary,
    evaluate_case,
    load_cases,
    write_reports,
)


DEFAULT_CASE_ROOT = PROJECT_ROOT / "tests" / "sql_test"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tests" / "sql_no_repair" / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SQL Harness ablation with repair disabled.")
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--category", default="", help="Run one category, for example simple_test.")
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N cases.")
    parser.add_argument("--timestamp-report", action="store_true")
    return parser.parse_args()


def resolve_report_paths(output_dir: Path, timestamp_report: bool) -> tuple[Path, Path]:
    suffix = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if timestamp_report else ""
    return (
        output_dir / f"no_repair_eval_report{suffix}.json",
        output_dir / f"no_repair_eval_report{suffix}.csv",
    )


def normalize_summary(summary: dict) -> dict:
    normalized = dict(summary)
    normalized["experiment"] = {
        "name": "SQL Harness without Repair",
        "description": "Uses Harness prompt and validation, but max_retries is fixed to 0.",
        "disabled_harness_features": ["retry", "auto repair"],
    }
    return normalized


def main() -> int:
    args = parse_args()
    cases, health = load_cases(args.case_root)

    if args.category:
        cases = [case for case in cases if case.category == args.category]
    if args.limit > 0:
        cases = cases[: args.limit]

    if not cases:
        print("No SQL cases found.")
        return 1

    agent = Text2SQLAgent()
    results = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id}")
        results.append(evaluate_case(agent, case, max_retries=0))

    summary = normalize_summary(build_summary(results, health))
    json_path, csv_path = resolve_report_paths(args.output_dir, args.timestamp_report)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    write_reports(results, summary, json_path, csv_path)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
