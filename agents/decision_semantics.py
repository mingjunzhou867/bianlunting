"""Single source of truth for decision semantics across backend and frontend."""
from __future__ import annotations

from typing import Any

from agents.base_agent import (
    CONCLUSION_FAIL,
    CONCLUSION_MISSING,
    CONCLUSION_PASS,
    STANCE_OPPOSE,
    STANCE_PENDING,
    STANCE_SUPPORT,
)

CLAUSE_STATUS_UNVERIFIED = "未证实"
CLAUSE_STATUS_NO_RISK = "未发现风险"
CLAUSE_STATUS_NEEDS_SUPPLEMENT = "待补充"

RULE_CATEGORY_BASIC = "basic"
RULE_CATEGORY_EXCLUSION = "exclusion"
RULE_CATEGORY_OTHER = "other"

EVIDENCE_STATE_HIT = "hit"
EVIDENCE_STATE_NOT_HIT = "not_hit"
EVIDENCE_STATE_MISSING_DATA = "missing_data"
EVIDENCE_STATE_UNKNOWN = "unknown"

DECISION_EFFECT_SUPPORT = "support"
DECISION_EFFECT_OPPOSE = "oppose"
DECISION_EFFECT_NEUTRAL = "neutral"


def normalize_rule_category(
    raw_category: str | None,
    *,
    fallback_category: str | None = None,
) -> str:
    category = (fallback_category or raw_category or "").strip().lower()
    if category in {RULE_CATEGORY_BASIC, RULE_CATEGORY_EXCLUSION}:
        return category
    source = str(raw_category or "")
    if "排除" in source:
        return RULE_CATEGORY_EXCLUSION
    if "基础" in source or "必须满足" in source:
        return RULE_CATEGORY_BASIC
    return RULE_CATEGORY_OTHER


def build_item_semantics(
    item: Any,
    *,
    category_hint: str | None = None,
) -> dict[str, Any]:
    category_code = normalize_rule_category(
        getattr(item, "category", None),
        fallback_category=category_hint,
    )
    exec_status = str(getattr(item, "exec_status", "") or "")
    supports_conclusion = getattr(item, "supports_conclusion", None)
    missing_data = exec_status in {"failed", "field_missing", "no_data"}

    if category_code == RULE_CATEGORY_EXCLUSION:
        if supports_conclusion is False:
            evidence_state = EVIDENCE_STATE_HIT
            decision_effect = DECISION_EFFECT_OPPOSE
            status = CONCLUSION_FAIL
            display_label = "反向证据"
            tag_type = "danger"
        elif supports_conclusion is True and not missing_data:
            evidence_state = EVIDENCE_STATE_HIT
            decision_effect = DECISION_EFFECT_SUPPORT
            status = CONCLUSION_PASS
            display_label = CONCLUSION_PASS
            tag_type = "success"
        else:
            evidence_state = EVIDENCE_STATE_NOT_HIT if missing_data else EVIDENCE_STATE_UNKNOWN
            decision_effect = DECISION_EFFECT_NEUTRAL
            status = CLAUSE_STATUS_NO_RISK
            display_label = CLAUSE_STATUS_NO_RISK
            tag_type = "info" if missing_data else "warning"
    else:
        if missing_data:
            evidence_state = EVIDENCE_STATE_MISSING_DATA
            decision_effect = DECISION_EFFECT_NEUTRAL
            status = CLAUSE_STATUS_UNVERIFIED
            display_label = CLAUSE_STATUS_UNVERIFIED
            tag_type = "warning"
        elif supports_conclusion is True:
            evidence_state = EVIDENCE_STATE_HIT
            decision_effect = DECISION_EFFECT_SUPPORT
            status = CONCLUSION_PASS
            display_label = CONCLUSION_PASS
            tag_type = "success"
        elif supports_conclusion is False:
            evidence_state = EVIDENCE_STATE_HIT
            decision_effect = DECISION_EFFECT_OPPOSE
            status = CONCLUSION_FAIL
            display_label = CONCLUSION_FAIL
            tag_type = "danger"
        else:
            evidence_state = EVIDENCE_STATE_UNKNOWN
            decision_effect = DECISION_EFFECT_NEUTRAL
            status = CLAUSE_STATUS_UNVERIFIED
            display_label = CLAUSE_STATUS_UNVERIFIED
            tag_type = "warning"

    stance = {
        DECISION_EFFECT_SUPPORT: STANCE_SUPPORT,
        DECISION_EFFECT_OPPOSE: STANCE_OPPOSE,
        DECISION_EFFECT_NEUTRAL: STANCE_PENDING,
    }[decision_effect]

    return {
        "semantic_category": category_code,
        "semantic_evidence_state": evidence_state,
        "semantic_decision_effect": decision_effect,
        "semantic_status": status,
        "semantic_display_label": display_label,
        "semantic_tag_type": tag_type,
        "semantic_stance": stance,
        "semantic_is_missing_data": missing_data,
    }


def conclusion_tag_type(conclusion: str | None) -> str:
    if conclusion == CONCLUSION_PASS:
        return "success"
    if conclusion == CONCLUSION_FAIL:
        return "danger"
    return "warning"


def aggregate_final_conclusion_from_judgments(judgments: list[Any]) -> str:
    def effective_stance(judgment: Any) -> str:
        conclusion = getattr(judgment, "conclusion", None)
        if conclusion == CONCLUSION_PASS:
            return STANCE_SUPPORT
        if conclusion == CONCLUSION_FAIL:
            return STANCE_OPPOSE
        if conclusion == CONCLUSION_MISSING:
            return STANCE_PENDING
        return str(getattr(judgment, "stance", STANCE_PENDING) or STANCE_PENDING)

    if any(effective_stance(j) == STANCE_OPPOSE for j in judgments):
        return CONCLUSION_FAIL
    if any(effective_stance(j) == STANCE_SUPPORT for j in judgments):
        return CONCLUSION_PASS
    return CONCLUSION_MISSING
