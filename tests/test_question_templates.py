"""Tests for the question template registry."""
from __future__ import annotations

import unittest

from cognition.question_templates import (
    QuestionTemplateRegistry,
    QuestionType,
    build_default_question_templates,
)


class TestQuestionTemplates(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = QuestionTemplateRegistry.default()

    def test_default_templates_cover_all_required_types(self) -> None:
        template_types = {template.question_type for template in build_default_question_templates()}
        self.assertEqual(
            template_types,
            {
                QuestionType.BASIC,
                QuestionType.EXCL,
                QuestionType.INFER,
                QuestionType.CALC,
            },
        )

    def test_templates_keep_qualification_links(self) -> None:
        template = self.registry.get_by_question_id("EXCL_SHAREHOLDER")
        self.assertIsNotNone(template)
        assert template is not None
        self.assertEqual(template.qualification_item_id, "QI_EXCL_SHAREHOLDER")
        self.assertEqual(template.question_type, QuestionType.EXCL)

    def test_registry_can_query_by_type(self) -> None:
        basic_templates = self.registry.get_by_type(QuestionType.BASIC)
        self.assertGreaterEqual(len(basic_templates), 2)
        self.assertTrue(all(template.question_type == QuestionType.BASIC for template in basic_templates))

    def test_registry_can_query_by_qualification_item(self) -> None:
        templates = self.registry.get_by_qualification_item("QI_CALC_HISTORY_MONTHS")
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].question_id, "CALC_HISTORY_MONTHS")

    def test_unknown_scope_returns_stable_empty_result(self) -> None:
        templates = self.registry.get_for_policy("POLICY-FLEX", qualification_scope="UNKNOWN_SCOPE")
        self.assertEqual(templates, [])


if __name__ == "__main__":
    unittest.main()
