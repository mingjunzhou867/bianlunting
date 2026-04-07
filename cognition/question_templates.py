"""Reusable question templates for qualification-first evidence planning."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    BASIC = "BASIC"
    EXCL = "EXCL"
    INFER = "INFER"
    CALC = "CALC"


class QuestionTemplate(BaseModel):
    qualification_item_id: str
    question_id: str
    question_text: str
    question_type: QuestionType
    policy_scope: str = "灵活就业社保补贴"
    linked_policy_clauses: list[str] = Field(default_factory=list)
    linked_conflict_patterns: list[str] = Field(default_factory=list)
    expected_answer_shape: str
    suggested_evidence_targets: list[str] = Field(default_factory=list)
    suggested_fields: list[str] = Field(default_factory=list)
    time_semantics_hint: str = ""
    default_missing_evidence_behavior: str = "mark_unknown"


def build_default_question_templates() -> list[QuestionTemplate]:
    return [
        QuestionTemplate(
            qualification_item_id="QI_BASIC_ACTIVE_PERSON",
            question_id="BASIC_PERSON_ACTIVE",
            question_text="申请人是否处于存活且系统有效的基础状态？",
            question_type=QuestionType.BASIC,
            linked_policy_clauses=["基础资格核验"],
            expected_answer_shape="boolean_with_reason",
            suggested_evidence_targets=["person"],
            suggested_fields=["person.life_status", "person.system_status"],
            time_semantics_hint="以系统日期对应的当前状态为准",
            default_missing_evidence_behavior="treat_as_not_satisfied",
        ),
        QuestionTemplate(
            qualification_item_id="QI_BASIC_HARDSHIP_CATEGORY",
            question_id="BASIC_HARDSHIP_CATEGORY",
            question_text="申请人是否具有有效的就业困难人员认定类别？",
            question_type=QuestionType.BASIC,
            linked_policy_clauses=["就业困难人员认定"],
            expected_answer_shape="enum_or_missing",
            suggested_evidence_targets=["hardship_certification"],
            suggested_fields=[
                "hardship_certification.hardship_category",
                "hardship_certification.is_valid",
            ],
            time_semantics_hint="优先使用最近有效认定记录",
            default_missing_evidence_behavior="mark_unknown",
        ),
        QuestionTemplate(
            qualification_item_id="QI_EXCL_SHAREHOLDER",
            question_id="EXCL_SHAREHOLDER",
            question_text="申请人是否存在会触发排除的企业股东或工商主体身份？",
            question_type=QuestionType.EXCL,
            linked_policy_clauses=["排除条件", "工商身份"],
            linked_conflict_patterns=["历史记录并存", "注销主体歧义"],
            expected_answer_shape="boolean_with_conflict_note",
            suggested_evidence_targets=["company_shareholder", "company_info", "person"],
            suggested_fields=[
                "company_shareholder.is_valid",
                "company_info.company_type",
                "person.business_role",
            ],
            time_semantics_hint="需区分当前有效记录与历史注销记录",
            default_missing_evidence_behavior="search_adjacent_source",
        ),
        QuestionTemplate(
            qualification_item_id="QI_EXCL_UNIT_INSURANCE",
            question_id="EXCL_UNIT_INSURANCE",
            question_text="申请期间是否存在单位缴纳医保记录，导致不满足灵活就业补贴条件？",
            question_type=QuestionType.EXCL,
            linked_policy_clauses=["单位缴纳排除"],
            expected_answer_shape="time_window_boolean",
            suggested_evidence_targets=["social_insurance_payment"],
            suggested_fields=[
                "social_insurance_payment.insurer_status",
                "social_insurance_payment.pay_month",
            ],
            time_semantics_hint="按月判断申请期间的缴纳主体状态",
            default_missing_evidence_behavior="mark_unknown",
        ),
        QuestionTemplate(
            qualification_item_id="QI_INFER_FISCAL_SUPPORT",
            question_id="INFER_FISCAL_SUPPORT",
            question_text="申请人是否存在财政供养或类似公共部门供养的高风险线索？",
            question_type=QuestionType.INFER,
            linked_policy_clauses=["合理推断"],
            linked_conflict_patterns=["单位性质歧义"],
            expected_answer_shape="risk_signal",
            suggested_evidence_targets=["social_insurance_payment", "company_info"],
            suggested_fields=[
                "social_insurance_payment.company_id",
                "company_info.company_type",
            ],
            time_semantics_hint="结合历史缴费与单位性质做风险推断",
            default_missing_evidence_behavior="mark_unknown",
        ),
        QuestionTemplate(
            qualification_item_id="QI_CALC_HISTORY_MONTHS",
            question_id="CALC_HISTORY_MONTHS",
            question_text="申请人历史已领取月份与当前缴费月份是否满足精算核算需要？",
            question_type=QuestionType.CALC,
            linked_policy_clauses=["精算规则"],
            expected_answer_shape="numeric_or_windowed_series",
            suggested_evidence_targets=["subsidy_history", "social_insurance_payment"],
            suggested_fields=[
                "social_insurance_payment.pay_month",
                "social_insurance_payment.pay_base",
            ],
            time_semantics_hint="按月聚合并关注连续月份与已领月份上限",
            default_missing_evidence_behavior="search_adjacent_source",
        ),
    ]


class QuestionTemplateRegistry:
    def __init__(self, templates: list[QuestionTemplate] | None = None):
        self._templates = templates or build_default_question_templates()

    @classmethod
    def default(cls) -> "QuestionTemplateRegistry":
        return cls()

    def list_types(self) -> list[QuestionType]:
        return sorted({template.question_type for template in self._templates}, key=str)

    def get_by_type(self, question_type: QuestionType | str) -> list[QuestionTemplate]:
        normalized = QuestionType(question_type)
        return [
            template for template in self._templates if template.question_type == normalized
        ]

    def get_by_question_id(self, question_id: str) -> QuestionTemplate | None:
        for template in self._templates:
            if template.question_id == question_id:
                return template
        return None

    def get_by_qualification_item(self, qualification_item_id: str) -> list[QuestionTemplate]:
        return [
            template
            for template in self._templates
            if template.qualification_item_id == qualification_item_id
        ]

    def get_for_policy(
        self,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> list[QuestionTemplate]:
        if qualification_scope:
            scoped = [
                template
                for template in self._templates
                if qualification_scope in (
                    template.question_type.value,
                    template.qualification_item_id,
                    template.question_id,
                )
            ]
            if scoped:
                return scoped
            return []
        return list(self._templates)
