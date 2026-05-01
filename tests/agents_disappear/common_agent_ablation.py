"""Shared helpers for agent-chain ablation experiments."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import agents.debate_orchestrator as debate_module
from agents.agent_lenient import LenientBusinessAgent
from agents.agent_strict import StrictComplianceAgent
from agents.debate_orchestrator import DebateOrchestrator
from agents.debate_persistence import build_debate_result, serialize_evidence_bundle
from evidence.evidence_projection import EvidenceProjection
from tests.agents_test.multi_agent_eval import (
    aggregate,
    apply_eval_isolation,
    apply_eval_rule_semantics,
    build_collector,
    build_eval_task_context,
    evaluate_case_metrics,
    parse_policy,
    read_json,
    resolve_eval_isolation,
    resolve_persona_mode,
    write_json,
    write_summary_markdown,
)


DEFAULT_SAMPLES = PROJECT_ROOT / "tests" / "agents_test" / "policy_eval_samples.json"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "tests" / "agents_disappear" / "reports"


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    description: str
    output_name: str
    configure_orchestrator: Callable[[DebateOrchestrator], None]
    no_evidence_constraint: bool = False


def configure_single_agent(orchestrator: DebateOrchestrator) -> None:
    orchestrator.agents = [StrictComplianceAgent()]
    orchestrator.max_rounds = 0


def configure_pro_con(orchestrator: DebateOrchestrator) -> None:
    orchestrator.agents = [StrictComplianceAgent(), LenientBusinessAgent()]


def configure_full_agents(orchestrator: DebateOrchestrator) -> None:
    return None


EXPERIMENTS = {
    "single": ExperimentConfig(
        name="Single Agent",
        description="One strict-compliance agent directly judges from evidence, without multi-agent debate.",
        output_name="single_agent",
        configure_orchestrator=configure_single_agent,
    ),
    "pro_con": ExperimentConfig(
        name="Pro-Con Debate",
        description="Two-agent strict-vs-lenient debate with arbitration.",
        output_name="pro_con_debate",
        configure_orchestrator=configure_pro_con,
    ),
    "no_evidence": ExperimentConfig(
        name="No Evidence Constraint",
        description="Full agent set receives policy task context, but evidence cards are hidden from debate prompts.",
        output_name="no_evidence_constraint",
        configure_orchestrator=configure_full_agents,
        no_evidence_constraint=True,
    ),
}


def hidden_evidence_projection(bundle: Any, task_header: str, policy_scope: str) -> EvidenceProjection:
    return EvidenceProjection(
        task_header=task_header,
        target_person=bundle.id_card,
        policy_scope=(
            f"{policy_scope}\n"
            "[ABLATION_NO_EVIDENCE] Evidence cards are intentionally hidden in this ablation. "
            "Judge from the policy task context only."
        ),
        cards=[],
        uncertainty_markers=["Evidence cards hidden for no-evidence-constraint ablation."],
        total_cards=0,
        resolved_count=0,
        unresolved_count=0,
    )


def run_with_optional_hidden_evidence(config: ExperimentConfig, func: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    if not config.no_evidence_constraint:
        return func()

    original_project_evidence = debate_module.project_evidence
    debate_module.project_evidence = hidden_evidence_projection
    try:
        return func()
    finally:
        debate_module.project_evidence = original_project_evidence


def run_one_case(
    case: dict[str, Any],
    *,
    config: ExperimentConfig,
    sql_mode: str,
    persona_mode: str,
) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        total_start = time.perf_counter()
        policy = parse_policy(case["policy"])
        id_card = str(case["id_card"])

        collector = build_collector(policy, sql_mode)
        evidence_start = time.perf_counter()
        bundle = collector.collect_all(id_card, policy_id=policy.policy_id)
        apply_eval_rule_semantics(bundle, policy)
        evidence_time_sec = time.perf_counter() - evidence_start

        orchestrator = DebateOrchestrator()
        config.configure_orchestrator(orchestrator)
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

        result = build_debate_result(
            str(uuid.uuid4()),
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
            "experiment": config.output_name,
            "sql_mode": sql_mode,
            "persona_mode": persona_mode,
            "persona_enabled": use_persona,
            "eval_isolation_enabled": isolation_enabled,
            "performance": timing,
            "metrics": metrics,
            "result": result,
            "evidence": serialize_evidence_bundle(bundle),
        }

    return run_with_optional_hidden_evidence(config, _run)


def difficulty_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        grouped.setdefault(str(item.get("difficulty") or "unknown"), []).append(item)

    metrics = {difficulty: aggregate(items) for difficulty, items in sorted(grouped.items())}
    for difficulty, items in grouped.items():
        metrics[difficulty]["decision_quality_score"] = average_decision_quality_score(items)
    return metrics


def conflict_pass(metrics: dict[str, Any]) -> bool:
    if not metrics.get("should_identify_conflict"):
        return True
    return bool(metrics.get("conflict_identified"))


def compute_decision_quality_score(metrics: dict[str, Any]) -> float:
    rule_coverage_pass = float(metrics.get("rule_coverage_rate") or 0.0) >= 1.0
    score = (
        0.35 * float(bool(metrics.get("conclusion_correct")))
        + 0.25 * float(bool(metrics.get("reason_complete")))
        + 0.20 * float(bool(metrics.get("evidence_referenced")))
        + 0.10 * float(rule_coverage_pass)
        + 0.10 * float(conflict_pass(metrics))
    )
    return round(score, 4)


def attach_decision_quality_scores(results: list[dict[str, Any]]) -> None:
    for item in results:
        metrics = item.get("metrics", {})
        metrics["decision_quality_score"] = compute_decision_quality_score(metrics)


def average_decision_quality_score(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    scores = [float(item.get("metrics", {}).get("decision_quality_score") or 0.0) for item in results]
    return round(sum(scores) / len(scores), 4)


def write_case_csv(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "difficulty",
        "expected_conclusion",
        "actual_conclusion",
        "conclusion_correct",
        "decision_quality_score",
        "overall_passed",
        "reason_complete",
        "evidence_reference_rate",
        "conflict_identified",
        "consensus_reached",
        "agent_valid_response_rate",
        "total_time_sec",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            metrics = item["metrics"]
            writer.writerow(
                {
                    "case_id": item["case_id"],
                    "difficulty": item["difficulty"],
                    "expected_conclusion": metrics["expected_conclusion"],
                    "actual_conclusion": metrics["actual_conclusion"],
                    "conclusion_correct": metrics["conclusion_correct"],
                    "decision_quality_score": metrics["decision_quality_score"],
                    "overall_passed": metrics["overall_passed"],
                    "reason_complete": metrics["reason_complete"],
                    "evidence_reference_rate": metrics["evidence_reference_rate"],
                    "conflict_identified": metrics["conflict_identified"],
                    "consensus_reached": metrics["consensus_reached"],
                    "agent_valid_response_rate": metrics["agent_valid_response_rate"],
                    "total_time_sec": metrics["total_time_sec"],
                }
            )


def parse_common_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--case-id", default="")
    parser.add_argument("--difficulty", default="", help="Optional difficulty filter: simple, medium, complex.")
    parser.add_argument("--sql-mode", choices=["template", "dynamic"], default="template")
    parser.add_argument("--persona-mode", choices=["auto", "off", "full"], default="auto")
    return parser.parse_args()


def run_experiment(config: ExperimentConfig, args: argparse.Namespace) -> int:
    suite = read_json(args.samples)
    cases = list(suite.get("cases", []))
    if args.case_id:
        cases = [case for case in cases if case.get("case_id") == args.case_id]
    if args.difficulty:
        cases = [case for case in cases if str(case.get("difficulty") or "").lower() == args.difficulty.lower()]
    if args.limit > 0:
        cases = cases[: args.limit]

    if not cases:
        print("No agent cases found.")
        return 1

    output_dir = args.output_dir or (DEFAULT_OUTPUT_ROOT / config.output_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.get('case_id')}")
        results.append(
            run_one_case(
                case,
                config=config,
                sql_mode=args.sql_mode,
                persona_mode=args.persona_mode,
            )
        )

    attach_decision_quality_scores(results)
    summary = aggregate(results)
    summary["decision_quality_score"] = average_decision_quality_score(results)
    summary["experiment"] = {
        "name": config.name,
        "description": config.description,
        "output_name": config.output_name,
    }
    summary["difficulty_metrics"] = difficulty_metrics(results)

    payload = {
        "suite_id": suite.get("suite_id", ""),
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment": summary["experiment"],
        "summary": summary,
        "results": results,
    }
    write_json(output_dir / "latest_results.json", payload)
    write_summary_markdown(output_dir / "latest_summary.md", suite, results, summary)
    write_case_csv(output_dir / "latest_results.csv", results)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON report: {output_dir / 'latest_results.json'}")
    print(f"Markdown summary: {output_dir / 'latest_summary.md'}")
    print(f"CSV report: {output_dir / 'latest_results.csv'}")
    return 0
