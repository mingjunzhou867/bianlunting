"""Tests for the question-driven evidence planner."""
from __future__ import annotations

import unittest

from cognition.evidence_planner import (
    EvidencePlan,
    MissingEvidenceStrategy,
    PlannerPriority,
    plan_evidence,
)


class TestEvidencePlanner(unittest.TestCase):
    def test_plan_evidence_returns_question_driven_items(self) -> None:
        plan = plan_evidence("42090219760310000D", "POLICY-FLEX")
        self.assertIsInstance(plan, EvidencePlan)
        self.assertGreater(len(plan.items), 0)
        self.assertTrue(all(item.question_id for item in plan.items))
        self.assertTrue(all(item.plan_item_id.startswith("plan_") for item in plan.items))

    def test_priority_order_places_basic_and_excl_first(self) -> None:
        plan = plan_evidence("42090219760310000D", "POLICY-FLEX")
        priorities = [item.priority for item in plan.items]
        self.assertIn(PlannerPriority.HIGH, priorities[:2])

    def test_traceability_fields_are_present(self) -> None:
        plan = plan_evidence("42090219760310000D", "POLICY-FLEX")
        first = plan.items[0]
        self.assertTrue(first.qualification_item_id)
        self.assertTrue(first.question_id)
        self.assertTrue(first.linked_policy_clauses is not None)

    def test_scope_filter_can_reduce_templates(self) -> None:
        plan = plan_evidence(
            "42090219760310000D",
            "POLICY-FLEX",
            qualification_scope="QI_BASIC_ACTIVE_PERSON",
        )
        self.assertEqual(len(plan.items), 1)
        self.assertEqual(plan.items[0].qualification_item_id, "QI_BASIC_ACTIVE_PERSON")

    def test_missing_strategy_and_sql_separation(self) -> None:
        plan = plan_evidence("42090219760310000D", "POLICY-FLEX")
        first = plan.items[0]
        self.assertIsInstance(first.missing_evidence_strategy, MissingEvidenceStrategy)
        self.assertFalse(hasattr(first, "sql"))
        self.assertTrue(all("SELECT " not in note for note in first.notes_for_query_generation))


if __name__ == "__main__":
    unittest.main()
