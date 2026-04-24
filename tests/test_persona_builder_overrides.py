from __future__ import annotations

import unittest

from evidence.evidence_model import EvidenceBundle, EvidenceItem
from portrait.persona_builder import PersonContext, PersonaBuilder


def _mock_context(life_status: str = "死亡") -> PersonContext:
    return PersonContext(
        person={
            "id_card": "42090219700505000I",
            "name": "测试用户",
            "gender": "男",
            "birth_date": "1970-05-05",
            "hukou_region": "湖北",
            "life_status": life_status,
            "system_status": "有效",
            "business_role": "",
        },
        unemployment=None,
        hardship=None,
        active_employment=None,
        employment_history=[],
        personal_payments=[],
        unit_payments=[],
        change_logs=[],
        subsidy_rows=[],
        shareholder_rows=[],
        legal_person_rows=[],
        inactive_self_business_rows=[],
    )


def _read_life_status_from_cards(profile: dict) -> str:
    cards = profile.get("fact_cards") or []
    for card in cards:
        if card.get("label") == "户籍 / 生存状态":
            value = str(card.get("value") or "")
            if "/" in value:
                return value.rsplit("/", 1)[-1].strip()
            return value.strip()
    return ""


class PersonaBuilderEvidenceOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = PersonaBuilder()
        self.builder._load_context = lambda _id_card: _mock_context("死亡")  # type: ignore[method-assign]

    def test_manual_support_overrides_death_status_for_persona(self) -> None:
        bundle = EvidenceBundle(
            id_card="42090219700505000I",
            items=[
                EvidenceItem(
                    evidence_id="manual_1",
                    rule_id="P001_MUST_001",
                    target_id_card="42090219700505000I",
                    target="person.life_status",
                    category="manual_supplement",
                    sql="",
                    result_raw=[],
                    result_summary="人工核验支持该条款：该人确认存活",
                    supports_conclusion=True,
                    confidence=1.0,
                    exec_status="success",
                    manual_verified=True,
                    manual_stance="support",
                )
            ],
        )

        profile = self.builder.build(id_card="42090219700505000I", evidence_bundle=bundle)
        self.assertEqual(_read_life_status_from_cards(profile), "生存")

    def test_manual_refute_keeps_death_status_for_persona(self) -> None:
        bundle = EvidenceBundle(
            id_card="42090219700505000I",
            items=[
                EvidenceItem(
                    evidence_id="manual_2",
                    rule_id="P001_MUST_001",
                    target_id_card="42090219700505000I",
                    target="person.life_status",
                    category="manual_supplement",
                    sql="",
                    result_raw=[],
                    result_summary="人工核验反驳该条款：生命状态异常",
                    supports_conclusion=False,
                    confidence=1.0,
                    exec_status="success",
                    manual_verified=True,
                    manual_stance="refute",
                )
            ],
        )

        profile = self.builder.build(id_card="42090219700505000I", evidence_bundle=bundle)
        self.assertEqual(_read_life_status_from_cards(profile), "死亡")


if __name__ == "__main__":
    unittest.main()
