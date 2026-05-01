"""Standalone multi-agent evaluation harness.

This script is intentionally outside the FastAPI runtime. It reads policy/case
samples from JSON, runs evidence collection, debate, adjudication, and writes
evaluation artifacts under tests/agents_test/outputs by default.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.debate_orchestrator import DebateOrchestrator
from agents.debate_persistence import build_debate_result, serialize_evidence_bundle
from agents.base_agent import CONCLUSION_FAIL, CONCLUSION_MISSING, CONCLUSION_PASS
from cognition.evidence_planner import EvidencePlanner
from cognition.policy_rule_loader import PolicyRule, PolicyRuleSet
from evidence.evidence_model import EvidenceBundle
from text2sql.dynamic.dynamic_collector import DynamicEvidenceCollector


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
MUST_RULE_TYPES = {"\u5fc5\u987b\u6ee1\u8db3", "must_satisfy", "MUST"}
EXCLUDE_RULE_TYPES = {"\u5fc5\u987b\u6392\u9664", "must_exclude", "EXCLUDE"}
FLEX_RULE_HIT_SUPPORT = {
    "EVAL_MEDIUM_FLEX_002",
    "EVAL_MEDIUM_FLEX_004",
    "EVAL_MEDIUM_FLEX_005",
}
FLEX_RULE_HIT_OPPOSE = {
    "EVAL_MEDIUM_FLEX_003",
    "EVAL_MEDIUM_FLEX_006",
}
FLEX_RULE_NO_HIT_SUPPORT = {
    "EVAL_MEDIUM_FLEX_001",
    "EVAL_MEDIUM_FLEX_003",
    "EVAL_MEDIUM_FLEX_006",
}
EVAL_ISOLATION_SCOPE = (
    "[EVAL_ISOLATION] Use only the current JSON policy rules and evidence cards. "
    "Current evaluation date is 2026-04-28; dates on or before this date are already effective. "
    "Do not add original-system policy requirements, historical cases, persona facts, "
    "continuous-month requirements, shareholder/legal-person checks, subsidy-history checks, "
    "or date assumptions unless they are explicitly listed in this sample policy. "
    "Return one strict JSON object only, with exactly these keys: conclusion, stance, confidence, "
    "evidence_refs, reasoning, dissent_points, key_finding. conclusion must be one of 符合/不符合/数据缺失; "
    "stance must match conclusion: 符合=支持通过, 不符合=反对通过, 数据缺失=待定. "
    "evidence_refs and dissent_points must always be arrays, even when empty; reasoning and key_finding must be strings. "
    "For must_exclude/exclusion rules, no returned rows means 未发现风险 and must not be treated as 数据缺失. "
    "For flexible/inference/calculation rules, treat them as auxiliary context only; they cannot independently force 不符合 or 数据缺失 unless an explicit sample rule says so."
)


@dataclass(frozen=True)
class EvalPolicy:
    policy_id: str
    policy_name: str
    policy_type: str
    rules: list[PolicyRule]


class JsonPolicyRuleLoader:
    """PolicyRuleLoader-compatible adapter backed by one sample policy."""

    def __init__(self, policy: EvalPolicy):
        self.policy = policy

    def load_rules(self, policy_id: str) -> PolicyRuleSet:
        must_satisfy: list[PolicyRule] = []
        must_exclude: list[PolicyRule] = []
        flexible: list[PolicyRule] = []

        for rule in self.policy.rules:
            if rule.rule_type in MUST_RULE_TYPES:
                must_satisfy.append(rule)
            elif rule.rule_type in EXCLUDE_RULE_TYPES:
                must_exclude.append(rule)
            else:
                flexible.append(rule)

        return PolicyRuleSet(
            policy_id=policy_id,
            must_satisfy=must_satisfy,
            must_exclude=must_exclude,
            flexible=flexible,
        )


class TemplateSqlAgent:
    """Text2SQLAgent-compatible adapter that executes sample sql_template."""

    def generate_sql(self, plan_item: Any, person_id: str, error_feedback: str = "") -> str:
        sql = str(plan_item.sql_template or "").strip()
        if not sql:
            raise ValueError(f"Sample rule {plan_item.rule_id} has empty sql_template")
        return sql


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def parse_policy(raw_policy: dict[str, Any]) -> EvalPolicy:
    rules: list[PolicyRule] = []
    for idx, raw_rule in enumerate(raw_policy.get("rules", []), start=1):
        rules.append(
            PolicyRule(
                rule_id=str(raw_rule["rule_id"]),
                rule_name=str(raw_rule.get("rule_name") or raw_rule["rule_id"]),
                rule_description=str(raw_rule.get("rule_description") or ""),
                rule_type=str(raw_rule.get("rule_type") or "flexible"),
                sql_template=str(raw_rule.get("sql_template") or ""),
                scenario_category=raw_rule.get("scenario_category"),
                priority=int(raw_rule.get("priority") or idx),
            )
        )

    return EvalPolicy(
        policy_id=str(raw_policy["policy_id"]),
        policy_name=str(raw_policy.get("policy_name") or raw_policy["policy_id"]),
        policy_type=str(raw_policy.get("policy_type") or "evaluation_policy"),
        rules=rules,
    )


def build_collector(policy: EvalPolicy, sql_mode: str) -> DynamicEvidenceCollector:
    collector = DynamicEvidenceCollector()
    collector.planner = EvidencePlanner(rule_loader=JsonPolicyRuleLoader(policy))
    if sql_mode == "template":
        collector.auto_debugger.agent = TemplateSqlAgent()
    return collector


def is_effective_hit(raw_data: list[dict[str, Any]]) -> bool:
    if not raw_data:
        return False
    if len(raw_data) == 1 and isinstance(raw_data[0], dict):
        row = raw_data[0]
        for key in ("cnt", "count"):
            if key in row:
                try:
                    return float(row.get(key) or 0) > 0
                except (TypeError, ValueError):
                    return False
    return True


def apply_eval_rule_semantics(evidence_bundle: EvidenceBundle, policy: EvalPolicy) -> None:
    """Apply deterministic hard-rule semantics for standalone EVAL_* samples."""

    rules_by_id = {rule.rule_id: rule for rule in policy.rules}
    for item in evidence_bundle.items:
        if not item.rule_id.startswith("EVAL_"):
            continue

        rule = rules_by_id.get(item.rule_id)
        if not rule:
            continue

        has_hit = is_effective_hit(item.result_raw)
        if rule.rule_type in MUST_RULE_TYPES:
            item.category = "basic"
            if item.exec_status == "success" and has_hit:
                item.supports_conclusion = True
            elif item.exec_status in {"success", "no_data"} and not has_hit:
                item.supports_conclusion = False
                item.result_summary = item.result_summary or "No effective record found for this required condition."
            continue

        if rule.rule_type in EXCLUDE_RULE_TYPES:
            item.category = "exclusion"
            if item.exec_status == "success" and has_hit:
                item.supports_conclusion = False
            elif item.exec_status in {"success", "no_data"} and not has_hit:
                item.supports_conclusion = True
                item.exec_status = "success"
                item.confidence = 1.0
                item.result_summary = (
                    "This is an exclusion rule. The SQL query returned no matching records, "
                    "so the exclusion risk is not hit and this rule should be treated as 未发现风险, not 数据缺失."
                )
                item.diagnostic_code = "ok"
                item.diagnostic_label = "Business-resolved no-hit exclusion"
                item.diagnostic_detail = "No database row was found for an exclusion rule; in this evaluation sample that means the risk is absent."
                item.diagnostic_hint = "No supplemental material is required for this exclusion rule."
            continue

        item.category = "flexible"
        if item.rule_id in FLEX_RULE_HIT_SUPPORT:
            if item.exec_status == "success" and has_hit:
                item.supports_conclusion = True
            elif item.exec_status == "no_data":
                item.supports_conclusion = None
            continue

        if item.rule_id in FLEX_RULE_HIT_OPPOSE:
            if item.exec_status == "success" and has_hit:
                item.supports_conclusion = False
            elif item.exec_status in {"success", "no_data"} and not has_hit:
                item.supports_conclusion = True
                if item.exec_status == "no_data":
                    item.exec_status = "success"
                    item.confidence = 1.0
                item.result_summary = "No matching risk records were found for this flexible risk check, so it supports pass."
                item.diagnostic_code = "ok"
                item.diagnostic_label = "Business-resolved no-hit flexible risk"
                item.diagnostic_detail = "No row was found for a flexible risk query; in this evaluation sample that means the risk is absent."
                item.diagnostic_hint = "No supplemental material is required for this flexible risk check."
            continue

        if item.rule_id in FLEX_RULE_NO_HIT_SUPPORT and item.exec_status in {"success", "no_data"} and not has_hit:
            item.supports_conclusion = True
            if item.exec_status == "no_data":
                item.exec_status = "success"
                item.confidence = 1.0
            item.result_summary = "No matching records were found for this flexible check; in this evaluation sample it is treated as acceptable."
            item.diagnostic_code = "ok"
            item.diagnostic_label = "Business-resolved no-hit flexible check"
            continue

        item.category = "flexible"
        if item.exec_status in {"success", "no_data"} and not has_hit:
            item.supports_conclusion = None
            item.result_summary = item.result_summary or "No decisive auxiliary record found for this flexible rule."


def normalize_conclusion(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"pass", "eligible", "\u7b26\u5408", "\u901a\u8fc7"} or value == CONCLUSION_PASS:
        return "pass"
    if text in {"fail", "not_eligible", "not-eligible", "\u4e0d\u7b26\u5408", "\u4e0d\u901a\u8fc7"} or value == CONCLUSION_FAIL:
        return "fail"
    if text in {"missing", "uncertain", "unknown", "\u6570\u636e\u7f3a\u5931", "\u5f85\u5b9a"} or value == CONCLUSION_MISSING:
        return "missing"
    return text


def flatten_history_text(history: list[Any]) -> str:
    parts: list[str] = []
    for record in history:
        for judgment in record.judgments:
            parts.extend(
                [
                    str(judgment.conclusion),
                    str(judgment.stance),
                    str(judgment.reasoning),
                    str(judgment.key_finding),
                    " ".join(str(point) for point in judgment.dissent_points),
                    " ".join(str(ref) for ref in judgment.evidence_refs),
                ]
            )
    return "\n".join(parts)


def evidence_reference_rate(history: list[Any], expected_refs: list[str]) -> float:
    if not expected_refs:
        return 1.0

    text = flatten_history_text(history)
    matched = 0
    for ref in expected_refs:
        ref_text = str(ref)
        ref_plan = f"plan_{ref_text.lower()}"
        if ref_text in text or ref_plan in text:
            matched += 1
    return matched / len(expected_refs)


def contains_all_keywords(text: str, keywords: list[str]) -> bool:
    return all(str(keyword) in text for keyword in keywords)


def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    return any(str(keyword) in text for keyword in keywords)


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def is_fallback_judgment(judgment: Any) -> bool:
    key_finding = str(getattr(judgment, "key_finding", "") or "")
    reasoning = str(getattr(judgment, "reasoning", "") or "")
    fallback_markers = ["fallback", "agent execution failed", "Connection error"]
    haystack = f"{key_finding}\n{reasoning}"
    return any(marker in haystack for marker in fallback_markers)


def agent_metrics(history: list[Any]) -> dict[str, Any]:
    judgments = [judgment for record in history for judgment in record.judgments]
    fallback_count = sum(1 for judgment in judgments if is_fallback_judgment(judgment))
    confidence_values = [float(getattr(judgment, "confidence", 0.0) or 0.0) for judgment in judgments]
    distribution: dict[str, int] = {}
    for judgment in judgments:
        conclusion = normalize_conclusion(getattr(judgment, "conclusion", ""))
        distribution[conclusion] = distribution.get(conclusion, 0) + 1

    return {
        "agent_judgment_count": len(judgments),
        "fallback_judgment_count": fallback_count,
        "agent_valid_response_rate": safe_rate(len(judgments) - fallback_count, len(judgments)),
        "avg_agent_confidence": (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        ),
        "agent_conclusion_distribution": distribution,
    }


def diagnostic_counts(evidence_bundle: EvidenceBundle) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence_bundle.items:
        code = str(getattr(item, "diagnostic_code", "") or "unknown")
        counts[code] = counts.get(code, 0) + 1
    return counts


def evaluate_case_metrics(
    *,
    case: dict[str, Any],
    result: dict[str, Any],
    history: list[Any],
    evidence_bundle: EvidenceBundle,
    policy: EvalPolicy,
    timing: dict[str, float],
    persona_enabled: bool,
) -> dict[str, Any]:
    expected = case.get("expected", {})
    expected_conclusion = normalize_conclusion(expected.get("final_conclusion"))
    actual_conclusion = normalize_conclusion(result.get("final_conclusion"))

    reasoning_text = flatten_history_text(history)
    adjudication_text = json.dumps(result.get("adjudication_report", {}), ensure_ascii=False, default=str)
    arbiter_text = json.dumps(result.get("arbiter_result", {}), ensure_ascii=False, default=str)
    full_text = "\n".join([reasoning_text, adjudication_text, arbiter_text])

    reason_keywords = [str(item) for item in expected.get("reason_keywords", [])]
    conflict_keywords = [
        str(item)
        for item in expected.get(
            "conflict_keywords",
            ["\u51b2\u7a81", "\u77db\u76fe", "\u4e0d\u4e00\u81f4", "\u6392\u9664", "\u98ce\u9669", "\u590d\u6838"],
        )
    ]
    must_reference_rules = [str(item) for item in expected.get("must_reference_rules", [])]
    reference_rate = evidence_reference_rate(history, must_reference_rules)

    should_identify_conflict = bool(expected.get("should_identify_conflict", False))
    conflict_detected = contains_any_keyword(full_text, conflict_keywords)
    rules_count = len(policy.rules)
    covered_rule_ids = {item.rule_id for item in evidence_bundle.items}
    expected_rule_ids = {rule.rule_id for rule in policy.rules}
    rule_coverage_rate = safe_rate(len(expected_rule_ids & covered_rule_ids), len(expected_rule_ids))
    sql_executed_count = sum(
        1
        for item in evidence_bundle.items
        if item.exec_status not in {"failed", "field_missing"}
    )
    success_count = sum(1 for item in evidence_bundle.items if item.exec_status == "success")
    missing_count = sum(1 for item in evidence_bundle.items if item.exec_status == "no_data")
    failure_count = sum(1 for item in evidence_bundle.items if item.exec_status in {"failed", "field_missing"})
    keyword_hits = sum(1 for keyword in reason_keywords if str(keyword) in full_text)
    keyword_coverage_rate = safe_rate(keyword_hits, len(reason_keywords)) if reason_keywords else 1.0
    agent_stats = agent_metrics(history)

    conclusion_correct = bool(expected_conclusion and expected_conclusion == actual_conclusion)
    reason_complete = keyword_coverage_rate >= 1.0

    return {
        "expected_conclusion": expected_conclusion,
        "actual_conclusion": actual_conclusion,
        "conclusion_correct": conclusion_correct,
        "reason_complete": reason_complete,
        "reason_keyword_coverage_rate": keyword_coverage_rate,
        "evidence_reference_rate": reference_rate,
        "evidence_referenced": reference_rate >= float(expected.get("min_evidence_reference_rate", 1.0)),
        "should_identify_conflict": should_identify_conflict,
        "conflict_identified": conflict_detected if should_identify_conflict else None,
        "rules_count": rules_count,
        "rule_coverage_rate": rule_coverage_rate,
        "evidence_count": len(evidence_bundle.items),
        "evidence_success_rate": safe_rate(success_count, len(evidence_bundle.items)),
        "evidence_missing_rate": safe_rate(missing_count, len(evidence_bundle.items)),
        "evidence_failure_rate": safe_rate(failure_count, len(evidence_bundle.items)),
        "sql_success_rate": safe_rate(sql_executed_count, rules_count),
        "diagnostic_counts": diagnostic_counts(evidence_bundle),
        "failed_rules": evidence_bundle.failed_rules,
        "agent_judgment_count": agent_stats["agent_judgment_count"],
        "fallback_judgment_count": agent_stats["fallback_judgment_count"],
        "agent_valid_response_rate": agent_stats["agent_valid_response_rate"],
        "avg_agent_confidence": agent_stats["avg_agent_confidence"],
        "agent_conclusion_distribution": agent_stats["agent_conclusion_distribution"],
        "consensus_rate": float(result.get("consensus_rate") or 0.0),
        "consensus_reached": bool(result.get("is_consensus_reached")),
        "rounds_taken": int(result.get("rounds_taken") or 0),
        "persona_enabled": persona_enabled,
        "total_time_sec": timing.get("total_time_sec", 0.0),
        "evidence_time_sec": timing.get("evidence_time_sec", 0.0),
        "debate_time_sec": timing.get("debate_time_sec", 0.0),
        "avg_rule_evidence_time_sec": safe_rate(timing.get("evidence_time_sec", 0.0), rules_count),
        "overall_passed": (
            conclusion_correct
            and reason_complete
            and reference_rate >= float(expected.get("min_evidence_reference_rate", 1.0))
            and rule_coverage_rate >= 1.0
            and failure_count == 0
        ),
    }


def resolve_persona_mode(case: dict[str, Any], persona_mode: str) -> bool:
    if persona_mode == "full":
        return True
    if persona_mode == "off":
        return False
    return str(case.get("difficulty") or "").lower() == "complex"


def resolve_eval_isolation(case: dict[str, Any]) -> bool:
    return str(case.get("difficulty") or "").lower() in {"simple", "medium"}


def apply_eval_isolation(orchestrator: DebateOrchestrator, enabled: bool) -> None:
    if enabled:
        orchestrator._empirical_case_context = lambda agent, projection: None


def build_eval_task_context(policy: EvalPolicy, isolation_enabled: bool) -> tuple[str, str]:
    task_header = f"{policy.policy_name}{policy.policy_type}"
    policy_scope = policy.policy_name
    if isolation_enabled:
        task_header = f"{task_header}\n{EVAL_ISOLATION_SCOPE}"
        policy_scope = f"{policy_scope}\n{EVAL_ISOLATION_SCOPE}"
    return task_header, policy_scope


def run_one_case(case: dict[str, Any], sql_mode: str, persona_mode: str) -> dict[str, Any]:
    total_start = time.perf_counter()
    policy = parse_policy(case["policy"])
    id_card = str(case["id_card"])

    collector = build_collector(policy, sql_mode)
    evidence_start = time.perf_counter()
    bundle = collector.collect_all(id_card, policy_id=policy.policy_id)
    apply_eval_rule_semantics(bundle, policy)
    evidence_time_sec = time.perf_counter() - evidence_start

    orchestrator = DebateOrchestrator()
    isolation_enabled = resolve_eval_isolation(case)
    apply_eval_isolation(orchestrator, isolation_enabled)
    task_header, policy_scope = build_eval_task_context(policy, isolation_enabled)
    use_persona = resolve_persona_mode(case, persona_mode)
    debate_start = time.perf_counter()
    persona = orchestrator._build_persona(bundle, policy.policy_id, None) if use_persona else None
    history, final_record = orchestrator._execute_debate(
        bundle,
        task_header=task_header,
        policy_scope=policy_scope,
        persona_context=persona,
    )
    arbiter_result = orchestrator._build_arbiter_result(
        bundle,
        history,
        final_record,
        task_header,
        policy_scope,
    )
    adjudication_report = orchestrator._build_adjudication_report(
        policy.policy_id,
        bundle,
        history,
        final_record,
        arbiter_result,
    )
    debate_time_sec = time.perf_counter() - debate_start

    session_id = str(uuid.uuid4())
    result = build_debate_result(
        session_id,
        bundle,
        history,
        final_record,
        arbiter_result=arbiter_result,
        adjudication_report=adjudication_report,
        persona=persona,
    )
    result["policy_id"] = policy.policy_id
    timing = {
        "evidence_time_sec": round(evidence_time_sec, 4),
        "debate_time_sec": round(debate_time_sec, 4),
        "total_time_sec": round(time.perf_counter() - total_start, 4),
    }

    metrics = evaluate_case_metrics(
        case=case,
        result=result,
        history=history,
        evidence_bundle=bundle,
        policy=policy,
        timing=timing,
        persona_enabled=use_persona,
    )

    return {
        "case_id": case["case_id"],
        "difficulty": case.get("difficulty", ""),
        "id_card": id_card,
        "policy_id": policy.policy_id,
        "policy_name": policy.policy_name,
        "sql_mode": sql_mode,
        "persona_mode": persona_mode,
        "persona_enabled": use_persona,
        "eval_isolation_enabled": isolation_enabled,
        "performance": timing,
        "metrics": metrics,
        "result": result,
        "evidence": serialize_evidence_bundle(bundle),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "case_count": 0,
            "conclusion_accuracy": 0.0,
            "reason_completeness_rate": 0.0,
            "avg_evidence_reference_rate": 0.0,
            "overall_pass_rate": 0.0,
            "avg_rule_coverage_rate": 0.0,
            "avg_sql_success_rate": 0.0,
            "avg_agent_valid_response_rate": 0.0,
            "consensus_reached_rate": 0.0,
            "avg_total_time_sec": 0.0,
            "conflict_identification_rate": None,
        }

    metrics = [item["metrics"] for item in results]
    conflict_cases = [m for m in metrics if m["should_identify_conflict"]]
    return {
        "case_count": len(results),
        "conclusion_accuracy": sum(1 for m in metrics if m["conclusion_correct"]) / len(metrics),
        "reason_completeness_rate": sum(1 for m in metrics if m["reason_complete"]) / len(metrics),
        "avg_evidence_reference_rate": sum(float(m["evidence_reference_rate"]) for m in metrics) / len(metrics),
        "overall_pass_rate": sum(1 for m in metrics if m["overall_passed"]) / len(metrics),
        "avg_rule_coverage_rate": sum(float(m["rule_coverage_rate"]) for m in metrics) / len(metrics),
        "avg_sql_success_rate": sum(float(m["sql_success_rate"]) for m in metrics) / len(metrics),
        "avg_agent_valid_response_rate": sum(float(m["agent_valid_response_rate"]) for m in metrics) / len(metrics),
        "consensus_reached_rate": sum(1 for m in metrics if m["consensus_reached"]) / len(metrics),
        "avg_total_time_sec": sum(float(m["total_time_sec"]) for m in metrics) / len(metrics),
        "fallback_case_count": sum(1 for m in metrics if m["fallback_judgment_count"] > 0),
        "conflict_identification_rate": (
            sum(1 for m in conflict_cases if m["conflict_identified"]) / len(conflict_cases)
            if conflict_cases
            else None
        ),
    }


def write_summary_markdown(path: Path, suite: dict[str, Any], results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# Multi-Agent Evaluation Summary",
        "",
        f"- suite_id: `{suite.get('suite_id', '')}`",
        f"- generated_at: `{datetime.now(UTC).isoformat()}`",
        f"- case_count: `{summary['case_count']}`",
        f"- conclusion_accuracy: `{summary['conclusion_accuracy']:.2%}`",
        f"- overall_pass_rate: `{summary['overall_pass_rate']:.2%}`",
        f"- avg_rule_coverage_rate: `{summary['avg_rule_coverage_rate']:.2%}`",
        f"- avg_sql_success_rate: `{summary['avg_sql_success_rate']:.2%}`",
        f"- avg_agent_valid_response_rate: `{summary['avg_agent_valid_response_rate']:.2%}`",
        f"- consensus_reached_rate: `{summary['consensus_reached_rate']:.2%}`",
        f"- reason_completeness_rate: `{summary['reason_completeness_rate']:.2%}`",
        f"- avg_evidence_reference_rate: `{summary['avg_evidence_reference_rate']:.2%}`",
        f"- avg_total_time_sec: `{summary['avg_total_time_sec']:.2f}`",
        f"- fallback_case_count: `{summary['fallback_case_count']}`",
    ]
    if summary["conflict_identification_rate"] is not None:
        lines.append(f"- conflict_identification_rate: `{summary['conflict_identification_rate']:.2%}`")
    else:
        lines.append("- conflict_identification_rate: `N/A`")

    lines.extend(
        [
            "",
            "| Case | Difficulty | Expected | Actual | Conclusion | Rule Cov | SQL | Agent Valid | Consensus | Time(s) | Evidence Ref | Conflict |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for item in results:
        m = item["metrics"]
        conflict = "N/A" if m["conflict_identified"] is None else str(bool(m["conflict_identified"]))
        lines.append(
            "| {case_id} | {difficulty} | {expected} | {actual} | {conclusion} | {rule_cov:.2%} | {sql:.2%} | {agent:.2%} | {consensus} | {time_sec:.2f} | {ref:.2%} | {conflict} |".format(
                case_id=item["case_id"],
                difficulty=item["difficulty"],
                expected=m["expected_conclusion"],
                actual=m["actual_conclusion"],
                conclusion=str(bool(m["conclusion_correct"])),
                rule_cov=float(m["rule_coverage_rate"]),
                sql=float(m["sql_success_rate"]),
                agent=float(m["agent_valid_response_rate"]),
                consensus=str(bool(m["consensus_reached"])),
                time_sec=float(m["total_time_sec"]),
                ref=float(m["evidence_reference_rate"]),
                conflict=conflict,
            )
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run standalone multi-agent policy evaluation cases.")
    parser.add_argument(
        "--samples",
        type=Path,
        default=Path(__file__).resolve().parent / "policy_eval_samples.json",
        help="Path to evaluation sample JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for latest_results.json and latest_summary.md.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional max case count.")
    parser.add_argument("--case-id", default="", help="Optional single case id to run.")
    parser.add_argument(
        "--difficulty",
        default="",
        help="Optional difficulty filter, e.g. simple, medium, complex.",
    )
    parser.add_argument(
        "--sql-mode",
        choices=["template", "dynamic"],
        default="template",
        help="template executes sample sql_template; dynamic lets the configured LLM generate SQL.",
    )
    parser.add_argument(
        "--persona-mode",
        choices=["auto", "off", "full"],
        default="auto",
        help="auto enables persona only for complex cases; off disables it; full enables it for all cases.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite = read_json(args.samples)
    cases = list(suite.get("cases", []))
    if args.difficulty:
        difficulty = str(args.difficulty).strip().lower()
        cases = [case for case in cases if str(case.get("difficulty", "")).strip().lower() == difficulty]
    if args.case_id:
        cases = [case for case in cases if case.get("case_id") == args.case_id]
    if args.limit and args.limit > 0:
        cases = cases[: args.limit]

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for case in cases:
        case_id = str(case.get("case_id", ""))
        try:
            print(f"[agents-eval] running {case_id} ({case.get('difficulty', '')})")
            results.append(run_one_case(case, args.sql_mode, args.persona_mode))
        except Exception as exc:
            failures.append({"case_id": case_id, "error": str(exc)})
            print(f"[agents-eval] failed {case_id}: {exc}", file=sys.stderr)

    summary = aggregate(results)
    payload = {
        "suite_id": suite.get("suite_id", ""),
        "generated_at": datetime.now(UTC).isoformat(),
        "sql_mode": args.sql_mode,
        "persona_mode": args.persona_mode,
        "summary": summary,
        "failures": failures,
        "results": results,
    }

    write_json(args.output_dir / "latest_results.json", payload)
    write_summary_markdown(args.output_dir / "latest_summary.md", suite, results, summary)
    print(f"[agents-eval] wrote {args.output_dir / 'latest_results.json'}")
    print(f"[agents-eval] wrote {args.output_dir / 'latest_summary.md'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
