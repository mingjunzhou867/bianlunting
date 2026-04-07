"""Typed semantic packet models and builder interfaces for cognition prep."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from config.settings import settings


class SemanticTask(BaseModel):
    person_id: str = Field(description="Task person identifier")
    policy_id: str = Field(description="Task policy identifier")
    qualification_scope: str | None = Field(
        default=None,
        description="Optional narrowed qualification scope",
    )
    summary: str = Field(description="Short task summary")


class FieldSemanticCard(BaseModel):
    table_name: str
    field_name: str
    business_meaning: str
    aliases: list[str] = Field(default_factory=list)
    value_kind: Literal["coded", "direct"] = "direct"
    dict_ref: str | None = None
    notes: list[str] = Field(default_factory=list)

    @property
    def field_key(self) -> str:
        return f"{self.table_name}.{self.field_name}"


class RelationSemanticCard(BaseModel):
    left_entity: str
    right_entity: str
    relation: str
    join_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TimeSemanticCard(BaseModel):
    semantic_name: str
    rule: str
    granularity: Literal["day", "month", "year"] = "month"
    related_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DictExcerpt(BaseModel):
    dict_id: str
    field_name: str
    description: str
    relevant_values: dict[str, str] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    source_refs: list[dict[str, str]] = Field(default_factory=list)


class SemanticPacket(BaseModel):
    task: SemanticTask
    fields: list[FieldSemanticCard] = Field(default_factory=list)
    relations: list[RelationSemanticCard] = Field(default_factory=list)
    time_semantics: list[TimeSemanticCard] = Field(default_factory=list)
    dict_excerpt: list[DictExcerpt] = Field(default_factory=list)


class StaticSemanticProvider:
    def get_task_summary(
        self,
        person_id: str,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> str:
        scope = qualification_scope or "全量资格核验"
        return f"围绕政策 {policy_id} 对人员 {person_id} 执行 {scope} 的数据库语义准备"

    def get_fields(
        self,
        person_id: str,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> list[FieldSemanticCard]:
        return [
            FieldSemanticCard(
                table_name="person",
                field_name="hukou_region",
                business_meaning="户籍区域，决定是否属于政策适用地区",
                aliases=["户籍区域", "户籍所在地"],
                value_kind="direct",
            ),
            FieldSemanticCard(
                table_name="person",
                field_name="business_role",
                business_meaning="工商身份，用于识别是否属于法人或个体工商户排除项",
                aliases=["工商身份"],
                value_kind="coded",
                dict_ref="BUSINESS_ROLE",
            ),
            FieldSemanticCard(
                table_name="employment_registration",
                field_name="employment_form",
                business_meaning="就业形式，判断是否为灵活就业登记",
                aliases=["就业形式"],
                value_kind="coded",
                dict_ref="EMPLOYMENT_FORM",
            ),
            FieldSemanticCard(
                table_name="hardship_certification",
                field_name="hardship_category",
                business_meaning="就业困难人员认定类别",
                aliases=["困难类别"],
                value_kind="coded",
                dict_ref="ADC310",
            ),
            FieldSemanticCard(
                table_name="social_insurance_payment",
                field_name="insurer_status",
                business_meaning="社保缴费身份状态，识别单位缴纳与灵活就业缴纳差异",
                aliases=["缴费身份状态"],
                value_kind="coded",
                dict_ref="INSURER_STATUS",
            ),
            FieldSemanticCard(
                table_name="social_insurance_payment",
                field_name="pay_month",
                business_meaning="缴费月份，用于连续月数与时间窗口判断",
                aliases=["缴费月份"],
                value_kind="direct",
            ),
        ]

    def get_relations(
        self,
        person_id: str,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> list[RelationSemanticCard]:
        return [
            RelationSemanticCard(
                left_entity="person",
                right_entity="employment_registration",
                relation="person.id_card -> employment_registration.id_card",
                join_keys=["id_card"],
                notes=["用于判断是否存在有效灵活就业登记"],
            ),
            RelationSemanticCard(
                left_entity="person",
                right_entity="hardship_certification",
                relation="person.id_card -> hardship_certification.id_card",
                join_keys=["id_card"],
                notes=["用于判断是否属于就业困难人员类别"],
            ),
            RelationSemanticCard(
                left_entity="person",
                right_entity="social_insurance_payment",
                relation="person.id_card -> social_insurance_payment.id_card",
                join_keys=["id_card"],
                notes=["用于分析医保/养老的缴纳主体与连续月份"],
            ),
        ]

    def get_time_semantics(
        self,
        person_id: str,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> list[TimeSemanticCard]:
        return [
            TimeSemanticCard(
                semantic_name="current_status_at_system_date",
                rule=f"所有状态判断默认以系统日期 {settings.system_date} 为参考点",
                granularity="day",
                related_fields=["person.life_status", "person.system_status"],
            ),
            TimeSemanticCard(
                semantic_name="payment_continuity_window",
                rule="社保缴费连续性默认按月粒度分析，并关注最近有效月份",
                granularity="month",
                related_fields=["social_insurance_payment.pay_month"],
            ),
            TimeSemanticCard(
                semantic_name="qualification_history_window",
                rule="就业登记、失业登记、困难认定均需要区分当前有效记录与历史记录",
                granularity="month",
                related_fields=[
                    "employment_registration.sync_date",
                    "unemployment_registration.register_date",
                    "hardship_certification.apply_date",
                ],
            ),
        ]

    def get_dict_excerpts(
        self,
        person_id: str,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> list[DictExcerpt]:
        return [
            load_dictionary_excerpt(
                "ADC310",
                field_name="hardship_certification.hardship_category",
                relevant_keys=["050", "993", "990"],
            ),
            load_dictionary_excerpt(
                "INSURER_STATUS",
                field_name="social_insurance_payment.insurer_status",
                relevant_keys=["101", "102"],
            ),
            load_dictionary_excerpt(
                "EMPLOYMENT_FORM",
                field_name="employment_registration.employment_form",
            ),
            load_dictionary_excerpt(
                "BUSINESS_ROLE",
                field_name="person.business_role",
            ),
        ]


class SemanticPacketBuilder:
    def __init__(self, provider: StaticSemanticProvider | None = None):
        self.provider = provider or StaticSemanticProvider()

    def build(
        self,
        person_id: str,
        policy_id: str,
        qualification_scope: str | None = None,
    ) -> SemanticPacket:
        task = SemanticTask(
            person_id=person_id,
            policy_id=policy_id,
            qualification_scope=qualification_scope,
            summary=self.provider.get_task_summary(
                person_id=person_id,
                policy_id=policy_id,
                qualification_scope=qualification_scope,
            ),
        )
        return SemanticPacket(
            task=task,
            fields=self.provider.get_fields(person_id, policy_id, qualification_scope),
            relations=self.provider.get_relations(
                person_id,
                policy_id,
                qualification_scope,
            ),
            time_semantics=self.provider.get_time_semantics(
                person_id,
                policy_id,
                qualification_scope,
            ),
            dict_excerpt=self.provider.get_dict_excerpts(
                person_id,
                policy_id,
                qualification_scope,
            ),
        )


def load_dictionary_excerpt(
    dict_id: str,
    field_name: str,
    relevant_keys: list[str] | None = None,
    dict_dir: Path | None = None,
) -> DictExcerpt:
    base_dir = dict_dir or Path(__file__).resolve().parent.parent / "dicts"
    file_path = base_dir / f"{dict_id}.json"
    payload = json.loads(file_path.read_text(encoding="utf-8"))

    all_values = payload.get("values", {})
    key_filter = set(relevant_keys or [])
    if key_filter:
        relevant_values = {
            key: value for key, value in all_values.items() if key in key_filter
        }
    else:
        relevant_values = dict(all_values)

    return DictExcerpt(
        dict_id=dict_id,
        field_name=field_name,
        description=payload.get("description", dict_id),
        relevant_values=relevant_values,
        aliases=payload.get("aliases", []),
        notes=payload.get("notes", []),
        source_refs=payload.get("source_refs", []),
    )


def build_semantic_packet(
    person_id: str,
    policy_id: str,
    qualification_scope: str | None = None,
    provider: StaticSemanticProvider | None = None,
) -> SemanticPacket:
    builder = SemanticPacketBuilder(provider=provider)
    return builder.build(
        person_id=person_id,
        policy_id=policy_id,
        qualification_scope=qualification_scope,
    )
