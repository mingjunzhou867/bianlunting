"""Question-driven evidence planning interfaces for cognition prep."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from cognition.policy_rule_loader import PolicyRule, PolicyRuleLoader
from cognition.question_templates import (
    QuestionTemplate,
    QuestionTemplateRegistry,
    QuestionType,
)
from cognition.semantic_packet import SemanticPacketBuilder


class PlannerPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MissingEvidenceStrategy(str, Enum):
    MARK_UNKNOWN = "mark_unknown"
    TREAT_AS_NOT_SATISFIED = "treat_as_not_satisfied"
    SEARCH_ADJACENT_SOURCE = "search_adjacent_source"


class EvidencePlanItem(BaseModel):
    plan_item_id: str
    rule_id: str
    rule_name: str
    rule_description: str
    rule_type: str
    sql_template: str
    priority: int | PlannerPriority
    scenario_category: str | None = None
    qualification_item_id: str | None = None
    question_id: str | None = None
    question_text: str | None = None
    question_type: QuestionType | None = None
    evidence_targets: list[str] = Field(default_factory=list)
    relevant_fields: list[str] = Field(default_factory=list)
    allowed_fields: list[str] = Field(default_factory=list)
    entity_scope: list[str] = Field(default_factory=list)
    time_window_or_time_rule: str = ""
    expected_answer_shape: str = ""
    missing_evidence_strategy: MissingEvidenceStrategy = MissingEvidenceStrategy.MARK_UNKNOWN
    conflict_strategy: str = ""
    linked_policy_clauses: list[str] = Field(default_factory=list)
    notes_for_query_generation: list[str] = Field(default_factory=list)


class EvidencePlan(BaseModel):
    person_id: str
    policy_id: str
    qualification_scope: str | None = None
    packet_summary: str
    items: list[EvidencePlanItem] = Field(default_factory=list)


class EvidencePlanner:
    def __init__(
        self,
        packet_builder: SemanticPacketBuilder | None = None,
        rule_loader: PolicyRuleLoader | None = None,
        template_registry: QuestionTemplateRegistry | None = None,
    ):
        self.packet_builder = packet_builder or SemanticPacketBuilder()
        self.rule_loader = rule_loader or PolicyRuleLoader()
        self.template_registry = template_registry or QuestionTemplateRegistry.default()

    def plan(
        self,
        person_id: str,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> EvidencePlan:
        packet = self.packet_builder.build(person_id, policy_id, qualification_scope)
        rule_set = self.rule_loader.load_rules(policy_id)

        items: list[EvidencePlanItem] = [
            self._build_plan_item_from_rule(rule)
            for rule in rule_set.must_satisfy + rule_set.must_exclude + rule_set.flexible
        ]

        # Compatibility fallback for the earlier question-template planner.
        if not items:
            templates = self.template_registry.get_for_policy(policy_id, qualification_scope)
            items = [self._build_plan_item(packet, template, person_id) for template in templates]

        items.sort(key=lambda item: (self._priority_rank(item.priority), item.rule_id))

        return EvidencePlan(
            person_id=person_id,
            policy_id=policy_id,
            qualification_scope=qualification_scope,
            packet_summary=packet.task.summary,
            items=items,
        )

    def _build_plan_item_from_rule(self, rule: PolicyRule) -> EvidencePlanItem:
        allowed_fields: list[str] = []
        relevant_fields: list[str] = []
        evidence_targets: list[str] = []
        notes_for_query_generation: list[str] = []

        if rule.rule_id == "P001_MUST_003":
            allowed_fields = [
                "hardship_certification.id_card",
                "hardship_certification.hardship_category",
                "hardship_certification.hardship_category_code",
                "hardship_certification.hardship_policy_match",
                "hardship_certification.apply_date",
                "hardship_certification.certify_org",
                "hardship_certification.is_valid",
            ]
            relevant_fields = list(allowed_fields)
            evidence_targets = [
                "hardship_certification",
                "person",
            ]
            notes_for_query_generation = [
                "This is a detail query. Use only real columns from the schema.",
                "Prefer field-level facts over COUNT(*).",
                "If hardship_certification lacks a needed field, fall back to the closest real fields and do not invent columns.",
            ]
        elif rule.rule_id == "P001_FLEX_002":
            allowed_fields = [
                "hardship_certification.id_card",
                "hardship_certification.hardship_category",
                "hardship_certification.hardship_category_code",
                "hardship_certification.hardship_policy_match",
                "hardship_certification.apply_date",
                "hardship_certification.certify_org",
                "hardship_certification.is_valid",
            ]
            relevant_fields = list(allowed_fields)
            evidence_targets = ["hardship_certification", "person"]
            notes_for_query_generation = [
                "This is a detail query. Use only real columns from the schema.",
                "Return actual hardship category facts or closest valid evidence.",
            ]
        elif rule.rule_id in {"P001_FLEX_004", "P001_FLEX_005"}:
            allowed_fields = [
                "social_insurance_payment.id_card",
                "social_insurance_payment.pay_month",
                "social_insurance_payment.insurance_type",
                "social_insurance_payment.pay_base",
                "social_insurance_payment.insurer_status",
                "subsidy_payment_history.id_card",
                "subsidy_payment_history.policy_code",
                "subsidy_payment_history.apply_start_month",
                "subsidy_payment_history.apply_end_month",
                "subsidy_payment_history.grant_months",
                "subsidy_payment_history.grant_amount",
            ]
            evidence_targets = ["social_insurance_payment", "subsidy_payment_history"]

        return EvidencePlanItem(
            plan_item_id=f"plan_{rule.rule_id.lower()}",
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            rule_description=rule.rule_description,
            rule_type=rule.rule_type,
            sql_template=rule.sql_template,
            priority=rule.priority,
            scenario_category=rule.scenario_category,
            relevant_fields=relevant_fields,
            allowed_fields=list(allowed_fields),
            evidence_targets=evidence_targets,
            notes_for_query_generation=notes_for_query_generation,
        )

    def _build_plan_item(
        self,
        packet: Any,
        template: QuestionTemplate,
        person_id: str,
    ) -> EvidencePlanItem:
        return EvidencePlanItem(
            plan_item_id=f"plan_{template.question_id.lower()}",
            rule_id=template.question_id,
            rule_name=template.question_id,
            rule_description=template.question_text,
            rule_type=self._rule_type_for(template.question_type),
            sql_template="",
            priority=self._priority_for(template.question_type),
            scenario_category=template.policy_scope,
            qualification_item_id=template.qualification_item_id,
            question_id=template.question_id,
            question_text=template.question_text,
            question_type=template.question_type,
            evidence_targets=list(template.suggested_evidence_targets),
            relevant_fields=self._select_relevant_fields(packet, template),
            entity_scope=[person_id],
            time_window_or_time_rule=self._time_rule_for(packet, template),
            expected_answer_shape=template.expected_answer_shape,
            missing_evidence_strategy=MissingEvidenceStrategy(
                template.default_missing_evidence_behavior
            ),
            conflict_strategy="preserve_trace_and_mark_for_review",
            linked_policy_clauses=list(template.linked_policy_clauses),
            notes_for_query_generation=[
                f"trace:{template.qualification_item_id}",
                f"question_type:{template.question_type.value}",
            ],
        )

    def _select_relevant_fields(self, packet: Any, template: QuestionTemplate) -> list[str]:
        packet_fields = {card.field_key for card in packet.fields}
        return [field for field in template.suggested_fields if field in packet_fields]

    def _time_rule_for(self, packet: Any, template: QuestionTemplate) -> str:
        for semantic in packet.time_semantics:
            if any(field in template.suggested_fields for field in semantic.related_fields):
                return semantic.rule
        return template.time_semantics_hint or "Use current task time semantics."

    def _priority_for(self, question_type: QuestionType) -> PlannerPriority:
        mapping = {
            QuestionType.BASIC: PlannerPriority.HIGH,
            QuestionType.EXCL: PlannerPriority.HIGH,
            QuestionType.INFER: PlannerPriority.MEDIUM,
            QuestionType.CALC: PlannerPriority.LOW,
        }
        return mapping[question_type]

    def _priority_rank(self, priority: int | PlannerPriority) -> int:
        if isinstance(priority, int):
            return priority
        return {
            PlannerPriority.HIGH: 0,
            PlannerPriority.MEDIUM: 1,
            PlannerPriority.LOW: 2,
        }[priority]

    def _rule_type_for(self, question_type: QuestionType) -> str:
        mapping = {
            QuestionType.BASIC: "蹇呴』婊¤冻",
            QuestionType.EXCL: "蹇呴』鎺掗櫎",
            QuestionType.INFER: "鐏垫椿璇勫垽",
            QuestionType.CALC: "鐏垫椿璇勫垽",
        }
        return mapping[question_type]


def plan_evidence(
    person_id: str,
    policy_id: str,
    qualification_scope: str | None = None,
    packet_builder: SemanticPacketBuilder | None = None,
    rule_loader: PolicyRuleLoader | None = None,
) -> EvidencePlan:
    planner = EvidencePlanner(
        packet_builder=packet_builder,
        rule_loader=rule_loader,
    )
    return planner.plan(
        person_id=person_id,
        policy_id=policy_id,
        qualification_scope=qualification_scope,
    )
