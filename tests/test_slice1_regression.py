"""Slice 1 regression tests for the adapter boundary."""
from __future__ import annotations

import inspect
import unittest

from agents.base_agent import format_evidence_bundle, format_projection
from agents.debate_orchestrator import (
    DEFAULT_POLICY_SCOPE,
    DEFAULT_TASK_HEADER,
    project_evidence,
)
from evidence.evidence_model import EvidenceBundle, EvidenceItem
from evidence.evidence_projection import EvidenceProjection, EvidenceSummaryCard


TASK_HEADER = DEFAULT_TASK_HEADER
POLICY_SCOPE = DEFAULT_POLICY_SCOPE
UNCERTAINTY_SECTION = "【不确定性标记】"
MISSING_LABEL = "证据缺失"


def _build_test_bundle() -> EvidenceBundle:
    return EvidenceBundle(
        id_card="42090219760310000D",
        items=[
            EvidenceItem(
                evidence_id="BASIC_001_000D",
                rule_id="BASIC_001",
                target_id_card="42090219760310000D",
                target="生存状态核查",
                category="基础条件",
                sql="SELECT 1",
                result_raw=[{"status": "生存"}],
                result_summary="该人员生存状态为“生存”，数据有效。",
                supports_conclusion=True,
                confidence=1.0,
                exec_status="success",
            ),
            EvidenceItem(
                evidence_id="EXCL_001_000D",
                rule_id="EXCL_001",
                target_id_card="42090219760310000D",
                target="个体工商户排查",
                category="排除条件",
                sql="SELECT 1",
                result_raw=[{"is_indi": "否"}],
                result_summary="未查到个体工商户登记，排除该排斥条件。",
                supports_conclusion=False,
                confidence=0.9,
                exec_status="success",
            ),
            EvidenceItem(
                evidence_id="INFER_001_000D",
                rule_id="INFER_001",
                target_id_card="42090219760310000D",
                target="财政供养人员推断",
                category="合理推断",
                sql="SELECT 1",
                result_raw=[],
                result_summary="无法确定是否为财政供养人员。",
                supports_conclusion=None,
                confidence=0.6,
                exec_status="success",
            ),
            EvidenceItem(
                evidence_id="BASIC_003_000D",
                rule_id="BASIC_003",
                target_id_card="42090219760310000D",
                target="灵活就业登记核查",
                category="基础条件",
                sql="SELECT 1",
                result_raw=[],
                result_summary="查询失败，数据库连接异常。",
                supports_conclusion=None,
                confidence=0.0,
                exec_status="failed",
            ),
            EvidenceItem(
                evidence_id="BASIC_004_000D",
                rule_id="BASIC_004",
                target_id_card="42090219760310000D",
                target="失业登记核查",
                category="基础条件",
                sql="SELECT 1",
                result_raw=[],
                result_summary="无失业登记数据。",
                supports_conclusion=None,
                confidence=0.5,
                exec_status="no_data",
            ),
        ],
    )


class TestProjectEvidence(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = _build_test_bundle()
        self.projection = project_evidence(self.bundle)

    def test_returns_evidence_projection_type(self) -> None:
        self.assertIsInstance(self.projection, EvidenceProjection)

    def test_task_header_and_policy_scope_are_set(self) -> None:
        self.assertEqual(self.projection.task_header, TASK_HEADER)
        self.assertEqual(self.projection.policy_scope, POLICY_SCOPE)

    def test_target_person_matches_bundle(self) -> None:
        self.assertEqual(self.projection.target_person, self.bundle.id_card)

    def test_total_cards_matches_items(self) -> None:
        self.assertEqual(self.projection.total_cards, len(self.bundle.items))
        self.assertEqual(len(self.projection.cards), 5)

    def test_status_mapping_supports(self) -> None:
        self.assertEqual(self._find_card("card_BASIC_001").status, "supports")

    def test_status_mapping_contradicts(self) -> None:
        self.assertEqual(self._find_card("card_EXCL_001").status, "contradicts")

    def test_status_mapping_unresolved(self) -> None:
        self.assertEqual(self._find_card("card_INFER_001").status, "unresolved")

    def test_status_mapping_missing(self) -> None:
        self.assertEqual(self._find_card("card_BASIC_003").status, "missing")
        self.assertEqual(self._find_card("card_BASIC_004").status, "missing")

    def test_resolved_and_unresolved_counts(self) -> None:
        self.assertEqual(self.projection.resolved_count, 2)
        self.assertEqual(self.projection.unresolved_count, 3)

    def test_uncertainty_markers_include_rule_ids(self) -> None:
        markers = " ".join(self.projection.uncertainty_markers)
        self.assertIn("INFER_001", markers)
        self.assertIn("BASIC_003", markers)
        self.assertIn("BASIC_004", markers)

    def test_card_fields_map_from_source(self) -> None:
        card = self._find_card("card_BASIC_001")
        self.assertEqual(card.question, self.bundle.items[0].target)
        self.assertEqual(card.finding, self.bundle.items[0].result_summary)
        self.assertEqual(card.artifact_refs, ["BASIC_001_000D"])

    def test_empty_bundle_produces_empty_projection(self) -> None:
        projection = project_evidence(EvidenceBundle(id_card="empty_test", items=[]))
        self.assertEqual(projection.total_cards, 0)
        self.assertEqual(projection.resolved_count, 0)
        self.assertEqual(projection.unresolved_count, 0)
        self.assertEqual(projection.cards, [])

    def _find_card(self, card_id: str) -> EvidenceSummaryCard:
        for card in self.projection.cards:
            if card.card_id == card_id:
                return card
        self.fail(f"Card {card_id} not found")


class TestFormatProjection(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = _build_test_bundle()
        self.projection = project_evidence(self.bundle)
        self.formatted = format_projection(self.projection)

    def test_output_contains_required_sections(self) -> None:
        self.assertIn("【任务】", self.formatted)
        self.assertIn("【取证对象】", self.formatted)
        self.assertIn("【政策范围】", self.formatted)
        self.assertIn("【证据概览】", self.formatted)
        self.assertIn(UNCERTAINTY_SECTION, self.formatted)

    def test_output_contains_cards_and_findings(self) -> None:
        self.assertIn("card_BASIC_001", self.formatted)
        self.assertIn(self.bundle.items[0].result_summary, self.formatted)
        self.assertIn(MISSING_LABEL, self.formatted)
        self.assertIn("BASIC_003", self.formatted)
        self.assertIn("failed", self.formatted)


class TestPromptTokenComparison(unittest.TestCase):
    def test_projection_format_not_significantly_larger_than_bundle_format(self) -> None:
        bundle = _build_test_bundle()
        old_text = format_evidence_bundle(bundle)
        new_text = format_projection(project_evidence(bundle))
        self.assertLessEqual(len(new_text), len(old_text) * 1.5)


class TestToolIsolation(unittest.TestCase):
    def test_project_evidence_source_does_not_reference_retrieval_tools(self) -> None:
        source = inspect.getsource(project_evidence)
        self.assertNotIn("text_to_sql", source)
        self.assertNotIn("get_dict", source)
        self.assertNotIn("auto_debug_sql", source)


if __name__ == "__main__":
    unittest.main()
