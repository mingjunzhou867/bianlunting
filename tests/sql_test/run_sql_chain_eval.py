"""Evaluate the Text2SQL chain with the SQL cases under tests/sql_test.

The case field named ``sql`` is treated as gold SQL. The evaluator compares
query results, not SQL strings, so equivalent SQL forms can pass.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from cognition.evidence_planner import EvidencePlanItem
from config.database import get_session
from text2sql.dynamic.text2sql_agent import Text2SQLAgent


DEFAULT_CASE_ROOT = Path(__file__).resolve().parent
DEFAULT_JSON_REPORT = DEFAULT_CASE_ROOT / "sql_chain_eval_report.json"
DEFAULT_CSV_REPORT = DEFAULT_CASE_ROOT / "sql_chain_eval_report.csv"
DEFAULT_REPORT_DIR = DEFAULT_CASE_ROOT / "reports"


@dataclass
class SqlCase:
    case_id: str
    category: str
    question: str
    gold_sql: str
    table: str = ""
    intent: str = ""
    source_file: str = ""


@dataclass
class AttemptResult:
    attempt_no: int
    generated_sql: str = ""
    generation_success: bool = False
    syntax_pass: bool = False
    execution_success: bool = False
    result_match: bool = False
    latency_ms: float = 0.0
    failure_reason: str = ""
    error_message: str = ""


@dataclass
class CaseResult:
    case_id: str
    category: str
    question: str
    gold_sql: str
    first_generated_sql: str = ""
    final_generated_sql: str = ""
    first_generation_success: bool = False
    first_syntax_pass: bool = False
    first_execution_success: bool = False
    first_result_match: bool = False
    retry_triggered: bool = False
    retry_count: int = 0
    retry_success: bool = False
    final_success: bool = False
    final_syntax_pass: bool = False
    final_execution_success: bool = False
    final_result_match: bool = False
    first_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    failure_reason: str = ""
    error_message: str = ""
    structural_warnings: list[str] = field(default_factory=list)
    has_structural_warnings: bool = False
    attempts: list[AttemptResult] = field(default_factory=list)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_category(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).parts[0]
    except ValueError:
        return path.parent.name


def load_cases(case_root: Path) -> tuple[list[SqlCase], list[dict[str, Any]]]:
    cases: list[SqlCase] = []
    health: list[dict[str, Any]] = []

    for path in sorted(case_root.rglob("*.json")):
        if "reports" in path.relative_to(case_root).parts:
            continue
        if path.name.startswith("sql_chain_eval_report"):
            continue

        item = {
            "file": str(path),
            "json_parse_success": False,
            "required_fields_present": 0,
            "case_count": 0,
            "error": "",
        }
        try:
            raw = read_json(path)
            item["json_parse_success"] = True
        except Exception as exc:
            item["error"] = str(exc)
            health.append(item)
            continue

        rows = raw.get("data", []) if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            item["error"] = "Top-level JSON must be a list or an object with a data list."
            health.append(item)
            continue

        category = normalize_category(path, case_root)
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            question = str(row.get("question") or "").strip()
            gold_sql = str(row.get("sql") or "").strip()
            if question and gold_sql:
                example_id = str(row.get("example_id") or f"{index:02d}").strip()
                cases.append(
                    SqlCase(
                        case_id=f"{category}:{example_id}",
                        category=category,
                        question=question,
                        gold_sql=gold_sql,
                        table=str(row.get("table") or "").strip(),
                        intent=str(row.get("intent") or "").strip(),
                        source_file=str(path),
                    )
                )
                item["required_fields_present"] += 1

        item["case_count"] = len(rows)
        health.append(item)

    return cases, health


def build_plan_item(case: SqlCase, person_id: str | None) -> EvidencePlanItem:
    tables = [part.strip() for part in case.table.split(",") if part.strip()]
    notes = [
        "Generate SQL for the natural language question only. Do not copy the gold SQL.",
        "Do not add filters, JOINs, validity constraints, or person filters that are not requested by the question.",
        "For record-detail questions, return the matching records from the target table; do not enrich with person names unless the question explicitly asks for names or person profile fields.",
        "If the question asks for all records, do not add is_valid/data_status filters unless validity is explicitly mentioned.",
    ]
    if person_id:
        notes.append(
            "The question explicitly contains an id_card. If filtering by id_card is needed, use id_card_replace."
        )
    else:
        notes.append(
            "This question does not contain an id_card. Do not add any id_card filter or default person scope."
        )

    return EvidencePlanItem(
        plan_item_id=case.case_id,
        rule_id=case.case_id,
        rule_name=case.question,
        rule_description=case.intent or case.question,
        rule_type="sql_chain_eval",
        sql_template="",
        priority=100,
        evidence_targets=tables,
        notes_for_query_generation=notes,
    )


def extract_person_id(text_value: str) -> str | None:
    match = re.search(r"(?<!\d)\d{17}[\dXx](?![\dXx])", text_value)
    return match.group(0) if match else None


def is_select_sql(sql: str) -> bool:
    cleaned = sql.strip().lstrip("(").strip().lower()
    return cleaned.startswith("select") or cleaned.startswith("with")


def strip_trailing_semicolon(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def execute_sql(sql: str) -> list[dict[str, Any]]:
    if not is_select_sql(sql):
        raise ValueError("Only SELECT/CTE SQL is allowed in this evaluator.")

    with get_session() as session:
        result = session.execute(text(sql))
        return [dict(row._mapping) for row in result.fetchall()]


def check_syntax(sql: str) -> tuple[bool, str]:
    if not is_select_sql(sql):
        return False, "Only SELECT/CTE SQL is allowed."

    try:
        with get_session() as session:
            session.execute(text(f"EXPLAIN {strip_trailing_semicolon(sql)}"))
        return True, ""
    except Exception as exc:
        return False, str(exc)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value.normalize())
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key): to_jsonable(value) for key, value in row.items()}


def ordered_query(sql: str) -> bool:
    lowered = sql.lower()
    return " order by " in lowered or " limit " in lowered


def compact_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().lower())


def has_join(sql: str) -> bool:
    return bool(re.search(r"\bjoin\b", compact_sql(sql)))


def has_field_filter(sql: str, field_name: str) -> bool:
    lowered = compact_sql(sql)
    where_match = re.search(r"\bwhere\b(.+?)(\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)", lowered)
    if not where_match:
        return False
    where_clause = where_match.group(1)
    return bool(
        re.search(
            rf"(?:\b\w+\.)?\b{re.escape(field_name.lower())}\b\s*(=|<>|!=|>|<|>=|<=|\bin\b|\bbetween\b|\blike\b|\bis\b)",
            where_clause,
        )
    )


def selected_columns_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    return list(rows[0].keys()) if rows else []


def detect_structural_warnings(
    gold_sql: str,
    generated_sql: str,
    gold_rows: list[dict[str, Any]],
    generated_rows: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if not has_join(gold_sql) and has_join(generated_sql):
        warnings.append("extra_join")

    for field_name in ("id_card", "is_valid", "data_status"):
        if not has_field_filter(gold_sql, field_name) and has_field_filter(generated_sql, field_name):
            warnings.append(f"extra_{field_name}_filter")

    gold_columns = selected_columns_from_rows(gold_rows)
    generated_columns = selected_columns_from_rows(generated_rows)
    if gold_columns and generated_columns:
        missing_columns = [column for column in gold_columns if column not in generated_columns]
        extra_columns = [column for column in generated_columns if column not in gold_columns]
        if missing_columns:
            warnings.append(f"missing_projection_columns={missing_columns}")
        if extra_columns:
            warnings.append(f"extra_projection_columns={extra_columns}")

    return warnings


def canonical_rows(rows: list[dict[str, Any]], preserve_order: bool) -> list[dict[str, Any]]:
    normalized = [normalize_row(row) for row in rows]
    if preserve_order:
        return normalized
    return sorted(normalized, key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))


def compare_result_sets(
    gold_sql: str,
    gold_rows: list[dict[str, Any]],
    generated_rows: list[dict[str, Any]],
) -> tuple[bool, str]:
    gold_columns = list(gold_rows[0].keys()) if gold_rows else []
    generated_columns = list(generated_rows[0].keys()) if generated_rows else []
    missing_columns = [column for column in gold_columns if column not in generated_columns]
    extra_columns = [column for column in generated_columns if column not in gold_columns]
    if missing_columns or extra_columns:
        return (
            False,
            "column_mismatch: "
            f"missing_columns={missing_columns}, extra_columns={extra_columns}, "
            f"gold_columns={gold_columns}, generated_columns={generated_columns}",
        )

    if len(gold_rows) != len(generated_rows):
        return False, f"row_count_mismatch: gold_rows={len(gold_rows)}, generated_rows={len(generated_rows)}"

    preserve_order = ordered_query(gold_sql)
    if canonical_rows(gold_rows, preserve_order) != canonical_rows(generated_rows, preserve_order):
        return False, f"value_mismatch: gold_rows={len(gold_rows)}, generated_rows={len(generated_rows)}"

    return True, ""


def result_sets_match(gold_sql: str, gold_rows: list[dict[str, Any]], generated_rows: list[dict[str, Any]]) -> bool:
    matched, _message = compare_result_sets(gold_sql, gold_rows, generated_rows)
    return matched


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return ordered[index]


def run_attempt(
    agent: Text2SQLAgent,
    case: SqlCase,
    gold_rows: list[dict[str, Any]],
    attempt_no: int,
    error_feedback: str,
) -> AttemptResult:
    started = time.perf_counter()
    attempt = AttemptResult(attempt_no=attempt_no)

    try:
        person_id = extract_person_id(case.question)
        prompt_person_id = person_id or ""
        generated_sql = agent.generate_sql(
            build_plan_item(case, person_id),
            prompt_person_id,
            error_feedback=error_feedback,
        )
        if person_id:
            generated_sql = generated_sql.replace("id_card_replace", person_id)
        generated_sql = generated_sql.strip()
        attempt.generated_sql = generated_sql
        attempt.generation_success = bool(generated_sql)
        if not attempt.generation_success:
            attempt.failure_reason = "generation_empty"
            return attempt
    except Exception as exc:
        attempt.failure_reason = "generation_error"
        attempt.error_message = str(exc)
        return attempt
    finally:
        attempt.latency_ms = (time.perf_counter() - started) * 1000

    syntax_ok, syntax_error = check_syntax(attempt.generated_sql)
    attempt.syntax_pass = syntax_ok
    if not syntax_ok:
        attempt.failure_reason = "syntax_error"
        attempt.error_message = syntax_error
        attempt.latency_ms = (time.perf_counter() - started) * 1000
        return attempt

    try:
        generated_rows = execute_sql(attempt.generated_sql)
        attempt.execution_success = True
    except (SQLAlchemyError, ValueError) as exc:
        attempt.failure_reason = "execution_error"
        attempt.error_message = str(exc)
        attempt.latency_ms = (time.perf_counter() - started) * 1000
        return attempt

    attempt.result_match, mismatch_message = compare_result_sets(case.gold_sql, gold_rows, generated_rows)
    if not attempt.result_match:
        attempt.failure_reason = "result_mismatch"
        attempt.error_message = mismatch_message

    attempt.latency_ms = (time.perf_counter() - started) * 1000
    return attempt


def evaluate_case(agent: Text2SQLAgent, case: SqlCase, max_retries: int) -> CaseResult:
    result = CaseResult(
        case_id=case.case_id,
        category=case.category,
        question=case.question,
        gold_sql=case.gold_sql,
    )
    started = time.perf_counter()

    try:
        gold_rows = execute_sql(case.gold_sql)
    except Exception as exc:
        result.failure_reason = "gold_sql_error"
        result.error_message = str(exc)
        result.total_latency_ms = (time.perf_counter() - started) * 1000
        return result

    error_feedback = ""
    attempts_to_run = max_retries + 1
    for attempt_no in range(1, attempts_to_run + 1):
        attempt = run_attempt(agent, case, gold_rows, attempt_no, error_feedback)
        result.attempts.append(attempt)

        if attempt_no == 1:
            result.first_generated_sql = attempt.generated_sql
            result.first_generation_success = attempt.generation_success
            result.first_syntax_pass = attempt.syntax_pass
            result.first_execution_success = attempt.execution_success
            result.first_result_match = attempt.result_match
            result.first_latency_ms = attempt.latency_ms

        if attempt.result_match:
            break

        error_feedback = (
            f"Previous attempt failed. Reason: {attempt.failure_reason}. "
            f"Error: {attempt.error_message}. SQL: {attempt.generated_sql}"
        )

    final_attempt = result.attempts[-1] if result.attempts else AttemptResult(attempt_no=0)
    result.final_generated_sql = final_attempt.generated_sql
    result.final_syntax_pass = final_attempt.syntax_pass
    result.final_execution_success = final_attempt.execution_success
    result.final_result_match = final_attempt.result_match
    result.final_success = final_attempt.result_match
    result.retry_count = max(0, len(result.attempts) - 1)
    result.retry_triggered = result.retry_count > 0
    result.retry_success = result.retry_triggered and result.final_success
    result.failure_reason = "" if result.final_success else final_attempt.failure_reason
    result.error_message = "" if result.final_success else final_attempt.error_message
    if final_attempt.execution_success and final_attempt.generated_sql:
        try:
            final_rows = execute_sql(final_attempt.generated_sql)
            result.structural_warnings = detect_structural_warnings(
                case.gold_sql,
                final_attempt.generated_sql,
                gold_rows,
                final_rows,
            )
            result.has_structural_warnings = bool(result.structural_warnings)
        except Exception as exc:
            result.structural_warnings = [f"structural_check_error={exc}"]
            result.has_structural_warnings = True
    result.total_latency_ms = (time.perf_counter() - started) * 1000
    return result


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def build_summary(results: list[CaseResult], health: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    retry_cases = [item for item in results if item.retry_triggered]
    final_latencies = [item.total_latency_ms for item in results]
    first_latencies = [item.first_latency_ms for item in results if item.first_latency_ms > 0]

    return {
        "total_cases": total,
        "testset_health": {
            "files": health,
            "json_parse_success_rate": rate(
                sum(1 for item in health if item["json_parse_success"]),
                len(health),
            ),
            "required_fields_present": sum(item["required_fields_present"] for item in health),
        },
        "sql_generation_success_rate": rate(
            sum(1 for item in results if item.first_generation_success),
            total,
        ),
        "first_syntax_pass_rate": rate(sum(1 for item in results if item.first_syntax_pass), total),
        "first_execution_success_rate": rate(
            sum(1 for item in results if item.first_execution_success),
            total,
        ),
        "first_result_match_rate": rate(sum(1 for item in results if item.first_result_match), total),
        "final_syntax_pass_rate": rate(sum(1 for item in results if item.final_syntax_pass), total),
        "final_execution_success_rate": rate(
            sum(1 for item in results if item.final_execution_success),
            total,
        ),
        "final_result_match_rate": rate(sum(1 for item in results if item.final_result_match), total),
        "retry_trigger_rate": rate(len(retry_cases), total),
        "retry_repair_success_rate": rate(sum(1 for item in retry_cases if item.retry_success), len(retry_cases)),
        "avg_retry_count": round(statistics.mean([item.retry_count for item in results]), 4) if results else 0.0,
        "first_avg_latency_ms": round(statistics.mean(first_latencies), 2) if first_latencies else 0.0,
        "final_avg_latency_ms": round(statistics.mean(final_latencies), 2) if final_latencies else 0.0,
        "p95_final_latency_ms": round(percentile(final_latencies, 95), 2),
        "failure_reasons": {
            reason: sum(1 for item in results if item.failure_reason == reason)
            for reason in sorted({item.failure_reason for item in results if item.failure_reason})
        },
        "structural_warning_rate": rate(sum(1 for item in results if item.has_structural_warnings), total),
        "structural_warnings": {
            warning: sum(1 for item in results if warning in item.structural_warnings)
            for warning in sorted({warning for item in results for warning in item.structural_warnings})
        },
    }


def write_reports(results: list[CaseResult], summary: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    payload = {
        "summary": summary,
        "cases": [asdict(item) for item in results],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "case_id",
        "category",
        "question",
        "gold_sql",
        "first_generated_sql",
        "final_generated_sql",
        "first_generation_success",
        "first_syntax_pass",
        "first_execution_success",
        "first_result_match",
        "retry_triggered",
        "retry_count",
        "retry_success",
        "final_success",
        "final_syntax_pass",
        "final_execution_success",
        "final_result_match",
        "first_latency_ms",
        "total_latency_ms",
        "failure_reason",
        "error_message",
        "has_structural_warnings",
        "structural_warnings",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            row = asdict(item)
            row.pop("attempts", None)
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SQL chain evaluation cases.")
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--csv-report", type=Path, default=DEFAULT_CSV_REPORT)
    parser.add_argument(
        "--report-prefix",
        default="",
        help="Write reports to tests/sql_test/reports/<prefix>.json and .csv.",
    )
    parser.add_argument(
        "--timestamp-report",
        action="store_true",
        help="Append a timestamp to reports generated with --report-prefix.",
    )
    parser.add_argument("--max-retries", type=int, default=2, help="Retries after the first failed attempt.")
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N cases.")
    parser.add_argument("--category", default="", help="Run one category, for example simple_test.")
    parser.add_argument(
        "--simple-all",
        action="store_true",
        help="Run all cases in tests/sql_test/simple_test.",
    )
    return parser.parse_args()


def apply_report_prefix(args: argparse.Namespace) -> None:
    if not args.report_prefix:
        return

    safe_prefix = re.sub(r"[^a-zA-Z0-9_.-]+", "_", args.report_prefix.strip())
    if args.timestamp_report:
        safe_prefix = f"{safe_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    args.json_report = DEFAULT_REPORT_DIR / f"{safe_prefix}.json"
    args.csv_report = DEFAULT_REPORT_DIR / f"{safe_prefix}.csv"


def main() -> int:
    args = parse_args()
    apply_report_prefix(args)
    cases, health = load_cases(args.case_root)
    if args.simple_all:
        args.category = "simple_test"
        args.limit = 0
    if args.category:
        cases = [case for case in cases if case.category == args.category]
    if args.limit > 0:
        cases = cases[: args.limit]

    if not cases:
        print("No SQL cases found.")
        return 1

    agent = Text2SQLAgent()
    results: list[CaseResult] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id}")
        results.append(evaluate_case(agent, case, max_retries=max(0, args.max_retries)))

    summary = build_summary(results, health)
    write_reports(results, summary, args.json_report, args.csv_report)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON report: {args.json_report}")
    print(f"CSV report: {args.csv_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
