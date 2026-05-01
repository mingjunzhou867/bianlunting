# AI辅助生成：deepseek V4 pro-2026-4-30
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.exc import SQLAlchemyError

from config.llm_client import llm_chat
from tests.sql_test.run_sql_chain_eval import (
    SqlCase,
    check_syntax,
    compare_result_sets,
    execute_sql,
    load_cases,
    percentile,
)

DEFAULT_CASE_ROOT = PROJECT_ROOT / "tests" / "sql_test"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tests" / "sql_disappear" / "reports"

@dataclass
class DirectCaseResult:
    case_id: str
    category: str
    question: str
    gold_sql: str
    generated_sql: str = ""
    generation_success: bool = False
    syntax_pass: bool = False
    execution_success: bool = False
    result_match: bool = False
    gold_sql_error: bool = False
    latency_ms: float = 0.0
    failure_reason: str = ""
    error_message: str = ""
    source_file: str = ""

def extract_sql(text: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip("` \n")

def generate_direct_sql(question: str) -> str:
    response = llm_chat(
        system_prompt=(
            "You generate SQL for a database task. "
            "Return only one SQL statement, with no explanation, no markdown, and no comments. "
            "Use only SELECT or WITH queries."
        ),
        user_message=question,
        temperature=0.0,
        max_tokens=600,
    )
    if not isinstance(response, str):
        raise ValueError(f"LLM returned non-text response: {response}")
    return extract_sql(response)

def evaluate_case(case: SqlCase) -> DirectCaseResult:
    result = DirectCaseResult(
        case_id=case.case_id,
        category=case.category,
        question=case.question,
        gold_sql=case.gold_sql,
        source_file=case.source_file,
    )

    try:
        gold_rows = execute_sql(case.gold_sql)
    except Exception as exc:
        result.gold_sql_error = True
        result.failure_reason = "gold_sql_error"
        result.error_message = str(exc)
        return result

    started = time.perf_counter()
    try:
        generated_sql = generate_direct_sql(case.question).strip()
        result.generated_sql = generated_sql
        result.generation_success = bool(generated_sql)
        if not result.generation_success:
            result.failure_reason = "generation_empty"
            return result
    except Exception as exc:
        result.failure_reason = "generation_error"
        result.error_message = str(exc)
        return result
    finally:
        result.latency_ms = (time.perf_counter() - started) * 1000

    syntax_ok, syntax_error = check_syntax(result.generated_sql)
    result.syntax_pass = syntax_ok
    if not syntax_ok:
        result.failure_reason = "syntax_error"
        result.error_message = syntax_error
        result.latency_ms = (time.perf_counter() - started) * 1000
        return result

    try:
        generated_rows = execute_sql(result.generated_sql)
        result.execution_success = True
    except (SQLAlchemyError, ValueError) as exc:
        result.failure_reason = "execution_error"
        result.error_message = str(exc)
        result.latency_ms = (time.perf_counter() - started) * 1000
        return result

    result.result_match, mismatch_message = compare_result_sets(case.gold_sql, gold_rows, generated_rows)
    if not result.result_match:
        result.failure_reason = "result_mismatch"
        result.error_message = mismatch_message

    result.latency_ms = (time.perf_counter() - started) * 1000
    return result

def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0

def build_metric_block(results: list[DirectCaseResult]) -> dict[str, Any]:
    total = len(results)
    eval_results = [item for item in results if not item.gold_sql_error]
    eval_total = len(eval_results)
    latencies = [item.latency_ms for item in eval_results if item.latency_ms > 0]

    return {
        "case_count": total,
        "evaluated_case_count": eval_total,
        "gold_sql_error_count": sum(1 for item in results if item.gold_sql_error),
        "sql_generation_success_rate": rate(sum(1 for item in eval_results if item.generation_success), eval_total),
        "syntax_pass_rate": rate(sum(1 for item in eval_results if item.syntax_pass), eval_total),
        "execution_success_rate": rate(sum(1 for item in eval_results if item.execution_success), eval_total),
        "result_match_rate": rate(sum(1 for item in eval_results if item.result_match), eval_total),
        "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
        "p95_latency_ms": round(percentile(latencies, 95), 2),
        "failure_reasons": {
            reason: sum(1 for item in results if item.failure_reason == reason)
            for reason in sorted({item.failure_reason for item in results if item.failure_reason})
        },
    }

def build_summary(results: list[DirectCaseResult]) -> dict[str, Any]:
    category_metrics = {}
    for category in sorted({item.category for item in results}):
        category_results = [item for item in results if item.category == category]
        category_metrics[category] = build_metric_block(category_results)

    summary = build_metric_block(results)
    summary["category_metrics"] = category_metrics
    return summary

def write_reports(
    results: list[DirectCaseResult],
    summary: dict[str, Any],
    json_path: Path,
    csv_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": {
            "name": "Direct LLM Baseline",
            "description": "Natural-language question directly generates SQL once, without SQL Harness features.",
            "disabled_harness_features": [
                "EvidencePlanItem",
                "schema notes",
                "retry",
                "auto repair",
                "structural drift check",
            ],
        },
        "summary": summary,
        "cases": [asdict(item) for item in results],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "case_id",
        "category",
        "question",
        "gold_sql",
        "generated_sql",
        "generation_success",
        "syntax_pass",
        "execution_success",
        "result_match",
        "gold_sql_error",
        "latency_ms",
        "failure_reason",
        "error_message",
        "source_file",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            writer.writerow({key: asdict(item).get(key, "") for key in fieldnames})

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Direct LLM SQL ablation evaluation.")
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--category", default="", help="Run one category, for example simple_test.")
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N cases.")
    parser.add_argument("--timestamp-report", action="store_true")
    return parser.parse_args()

def resolve_report_paths(output_dir: Path, timestamp_report: bool) -> tuple[Path, Path]:
    suffix = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if timestamp_report else ""
    return (
        output_dir / f"direct_llm_eval_report{suffix}.json",
        output_dir / f"direct_llm_eval_report{suffix}.csv",
    )

def main() -> int:
    args = parse_args()
    cases, _health = load_cases(args.case_root)

    if args.category:
        cases = [case for case in cases if case.category == args.category]
    if args.limit > 0:
        cases = cases[: args.limit]

    if not cases:
        print("No SQL cases found.")
        return 1

    results: list[DirectCaseResult] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id}")
        results.append(evaluate_case(case))

    summary = build_summary(results)
    json_path, csv_path = resolve_report_paths(args.output_dir, args.timestamp_report)
    write_reports(results, summary, json_path, csv_path)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
