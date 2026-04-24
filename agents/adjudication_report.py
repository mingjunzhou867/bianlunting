"""Build actionable adjudication reports from debate artifacts."""
from __future__ import annotations

import re
from typing import Any

from agents.base_agent import (
    CONCLUSION_FAIL,
    CONCLUSION_MISSING,
    CONCLUSION_PASS,
    STANCE_OPPOSE,
    STANCE_SUPPORT,
)
from agents.decision_semantics import (
    CLAUSE_STATUS_NEEDS_SUPPLEMENT,
    CLAUSE_STATUS_NO_RISK,
    CLAUSE_STATUS_UNVERIFIED,
    CONCLUSION_FAIL,
    CONCLUSION_PASS,
    DECISION_EFFECT_OPPOSE,
    build_item_semantics,
)
from evidence.evidence_model import EvidenceBundle, EvidenceItem
from policy.policy_models import PolicyRule
from policy.policy_router import get_policy

_RULE_ID_RE = re.compile(r"[A-Z]+_\d+")


def build_adjudication_report(
    *,
    policy_id: str,
    bundle: EvidenceBundle,
    history: list[Any],
    final_record: Any,
    arbiter_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = get_policy(policy_id)
    clause_results = _build_clause_results(policy_id, policy, bundle)
    debate_digest = _build_debate_digest(final_record)
    top_reason = _pick_top_reason(clause_results, final_record)
    next_actions = _build_next_actions(clause_results, final_record, top_reason)

    return {
        "summary": {
            "final_conclusion": final_record.get_final_conclusion(),
            "top_reason": top_reason,
            "confidence": round(float(arbiter_result.get("explanation_confidence", 0.0)) if arbiter_result else 0.0, 4),
        },
        "clause_results": clause_results,
        "debate_digest": debate_digest,
        "next_actions": next_actions,
        "meta": {
            "policy_id": policy_id,
            "policy_name": policy.policy_name if policy else policy_id,
            "rounds": len(history),
            "consensus_rate": round(float(final_record.consensus_rate), 4),
        },
    }


def _iter_policy_rules(policy: Any) -> list[tuple[str, PolicyRule]]:
    if policy is None:
        return []
    grouped: list[tuple[str, list[PolicyRule]]] = [
        ("basic", policy.structured_rules.basic_conditions),
        ("exclusion", policy.structured_rules.exclusion_conditions),
        ("inference", policy.structured_rules.inference_rules),
        ("calculation", policy.structured_rules.calculation_rules),
    ]
    rows: list[tuple[str, PolicyRule]] = []
    for category, rules in grouped:
        for rule in rules:
            rows.append((category, rule))
    return rows


def _build_clause_results(policy_id: str, policy: Any, bundle: EvidenceBundle) -> list[dict[str, Any]]:
    evidence_by_rule: dict[str, EvidenceItem] = bundle.by_rule
    clauses: list[dict[str, Any]] = []

    for category, rule in _iter_policy_rules(policy):
        item = evidence_by_rule.get(rule.rule_id)
        clauses.append(_make_clause_entry(category, rule, item))

    if clauses:
        return clauses

    # Fallback when policy definition is missing.
    for item in bundle.items:
        pseudo_rule = PolicyRule(rule_id=item.rule_id, description=item.target)
        clauses.append(_make_clause_entry("unknown", pseudo_rule, item))

    if not clauses:
        clauses.append(
            {
                "clause_id": "NO_RULES",
                "clause_text": f"Policy {policy_id} has no structured rules.",
                "status": CLAUSE_STATUS_NEEDS_SUPPLEMENT,
                "reason": "当前策略没有结构化条款，无法生成逐条判定。",
                "evidence_refs": [],
                "missing_fields": ["structured_rules"],
                "action_hint": "请先补齐 policy_master 中的 rule_definitions 配置。",
                "category": "unknown",
                "semantic_category": "unknown",
                "semantic_evidence_state": "missing_data",
                "semantic_decision_effect": "neutral",
                "semantic_status": CLAUSE_STATUS_NEEDS_SUPPLEMENT,
                "semantic_display_label": CLAUSE_STATUS_NEEDS_SUPPLEMENT,
                "semantic_tag_type": "warning",
                "semantic_stance": "",
                "semantic_is_missing_data": True,
            }
        )
    return clauses


def _make_clause_entry(category: str, rule: PolicyRule, item: EvidenceItem | None) -> dict[str, Any]:
    clause_text_parts = [rule.description]
    if rule.pass_condition:
        clause_text_parts.append(f"通过条件: {rule.pass_condition}")
    if rule.fail_condition:
        clause_text_parts.append(f"不通过条件: {rule.fail_condition}")
    clause_text = "；".join(part for part in clause_text_parts if part)

    if item is None:
        semantic = {
            "semantic_category": category,
            "semantic_evidence_state": "missing_data",
            "semantic_decision_effect": "neutral",
            "semantic_status": CLAUSE_STATUS_NEEDS_SUPPLEMENT,
            "semantic_display_label": CLAUSE_STATUS_NEEDS_SUPPLEMENT,
            "semantic_tag_type": "warning",
            "semantic_stance": "",
            "semantic_is_missing_data": True,
        }
        return {
            "clause_id": rule.rule_id,
            "clause_text": clause_text,
            "status": CLAUSE_STATUS_NEEDS_SUPPLEMENT,
            "reason": "未检索到该条款对应证据。",
            "evidence_refs": [],
            "missing_fields": [rule.rule_id],
            "action_hint": "补齐该条款对应的数据后重试。",
            "category": category,
            **semantic,
        }

    semantic = build_item_semantics(item, category_hint=category)
    status = semantic["semantic_status"]
    reason = _resolve_clause_reason(item, status, semantic)
    missing_fields = _resolve_missing_fields(item, status, semantic)
    return {
        "clause_id": rule.rule_id,
        "clause_text": clause_text,
        "status": status,
        "reason": reason,
        "evidence_refs": [item.evidence_id],
        "missing_fields": missing_fields,
        "action_hint": _resolve_action_hint(item, status, semantic),
        "category": category,
        **semantic,
    }


def _resolve_clause_reason(item: EvidenceItem, status: str, semantic: dict[str, Any]) -> str:
    if status == CONCLUSION_FAIL:
        return item.result_summary or item.diagnostic_detail or "证据结果与条款通过条件冲突。"
    if status == CONCLUSION_PASS:
        return item.result_summary or "该条款证据满足通过条件。"
    if status in {CLAUSE_STATUS_NO_RISK, CLAUSE_STATUS_UNVERIFIED, CLAUSE_STATUS_NEEDS_SUPPLEMENT}:
        return item.diagnostic_detail or item.result_summary or "该条款未能被证实，需补证或人工复核。"
    if semantic.get("semantic_status") == CLAUSE_STATUS_NO_RISK:
        return item.result_summary or item.diagnostic_detail or "未命中排除项，按未发现风险处理。"
    return item.diagnostic_detail or item.result_summary or "该必须满足项未被证实，需补证或人工复核。"


def _resolve_missing_fields(item: EvidenceItem, status: str, semantic: dict[str, Any]) -> list[str]:
    if status in {CONCLUSION_PASS, CONCLUSION_FAIL}:
        return []
    if item.diagnostic_code == "missing_column":
        return [item.rule_id, "required_column"]
    if item.diagnostic_code == "empty_result":
        return [item.rule_id, "required_records"]
    if semantic.get("semantic_category") == "exclusion":
        return [item.rule_id, "risk_check"]
    return [item.rule_id, "required_evidence"]


def _resolve_action_hint(item: EvidenceItem, status: str, semantic: dict[str, Any]) -> str:
    if status == CONCLUSION_PASS:
        return "该条款已满足，无需补充。"
    if status == CONCLUSION_FAIL:
        return "该条款不通过，建议核对业务事实或改走其他政策路径。"
    if semantic.get("semantic_status") == CLAUSE_STATUS_NO_RISK:
        return item.diagnostic_hint or "未命中排除项，按未发现风险处理，并保留为复核提示。"
    return item.diagnostic_hint or "该必须满足项未被证实，建议补充材料或人工复核。"


def _build_debate_digest(final_record: Any) -> dict[str, Any]:
    judgments = list(final_record.judgments or [])
    support_points: list[str] = []
    oppose_points: list[str] = []
    focus_clause_ids: list[str] = []
    seen_focus: set[str] = set()

    for j in judgments:
        point = (j.key_finding or j.reasoning or "").strip()
        if not point:
            continue
        if j.stance == STANCE_SUPPORT and len(support_points) < 2:
            support_points.append(f"{j.agent_role}: {point}")
        if j.stance == STANCE_OPPOSE and len(oppose_points) < 2:
            oppose_points.append(f"{j.agent_role}: {point}")
        for raw in [*j.evidence_refs, *j.dissent_points]:
            for cid in _extract_clause_ids(raw):
                if cid not in seen_focus:
                    seen_focus.add(cid)
                    focus_clause_ids.append(cid)
                if len(focus_clause_ids) >= 6:
                    break
            if len(focus_clause_ids) >= 6:
                break

    return {
        "support_points": support_points,
        "oppose_points": oppose_points,
        "focus_clauses": focus_clause_ids,
    }


def _extract_clause_ids(text: str) -> list[str]:
    if not text:
        return []
    direct = [m.group(0) for m in _RULE_ID_RE.finditer(text)]
    if direct:
        return direct
    if text.startswith("card_"):
        token = text.removeprefix("card_")
        return [token] if _RULE_ID_RE.fullmatch(token) else []
    return []


def _pick_top_reason(clause_results: list[dict[str, Any]], final_record: Any) -> str:
    fails = [row for row in clause_results if row.get("semantic_decision_effect") == DECISION_EFFECT_OPPOSE]
    if fails:
        hit = fails[0]
        return f"{hit.get('clause_id')}: {hit.get('reason')}"

    missing = [
        row
        for row in clause_results
        if row.get("status") in {CLAUSE_STATUS_UNVERIFIED, CLAUSE_STATUS_NEEDS_SUPPLEMENT}
    ]
    if missing:
        hit = missing[0]
        return f"{hit.get('clause_id')}: {hit.get('reason')}"

    if final_record.get_final_conclusion() == CONCLUSION_PASS:
        return "关键条款均满足，未发现硬性否决项。"
    if final_record.get_final_conclusion() == CONCLUSION_FAIL:
        return "存在关键条款不通过。"
    if final_record.get_final_conclusion() == CONCLUSION_MISSING:
        return "关键条款存在数据缺失。"
    return "已完成裁决。"


def _build_next_actions(
    clause_results: list[dict[str, Any]],
    final_record: Any,
    top_reason: str,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    missing = [
        row
        for row in clause_results
        if row.get("status") in {CLAUSE_STATUS_UNVERIFIED, CLAUSE_STATUS_NEEDS_SUPPLEMENT}
    ]
    risks = [row for row in clause_results if row.get("status") == CLAUSE_STATUS_NO_RISK]
    fails = [row for row in clause_results if row.get("semantic_decision_effect") == DECISION_EFFECT_OPPOSE]

    if final_record.get_final_conclusion() == CONCLUSION_MISSING:
        for row in missing[:3]:
            actions.append(
                {
                    "type": "补充材料",
                    "title": f"补齐 {row.get('clause_id')}",
                    "detail": row.get("action_hint") or row.get("reason") or "请补充相关资料。",
                }
            )
        if not actions:
            actions.append(
                {
                    "type": "补充材料",
                    "title": "补充关键缺失数据",
                    "detail": top_reason,
                }
            )
        return actions

    if final_record.get_final_conclusion() == CONCLUSION_FAIL:
        first = fails[0] if fails else None
        actions.append(
            {
                "type": "直接不通过",
                "title": "输出不符合结论",
                "detail": first.get("reason") if first else top_reason,
            }
        )
        if len(fails) > 1:
            actions.append(
                {
                    "type": "次要原因",
                    "title": f"附加不通过条款 {fails[1].get('clause_id')}",
                    "detail": fails[1].get("reason") or "",
                }
            )
        return actions

    actions.append(
        {
            "type": "可办理",
            "title": "符合办理条件",
            "detail": "建议进入办理流程并保留本次裁决证据。",
        }
    )
    if risks:
        actions.append(
            {
                "type": "风险提示",
                "title": "保留未命中排除项风险提示",
                "detail": risks[0].get("reason") or risks[0].get("action_hint") or "",
            }
        )
    if missing:
        actions.append(
            {
                "type": "补证提示",
                "title": "存在未证实的必须满足项",
                "detail": missing[0].get("action_hint") or missing[0].get("reason") or "",
            }
        )
    return actions
