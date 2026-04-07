from __future__ import annotations

import unittest
from types import SimpleNamespace

from text2sql.dynamic.dynamic_collector import DynamicEvidenceCollector


class DynamicCollectorNoDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.collector = DynamicEvidenceCollector()

    def test_identity_switch_no_data_is_treated_as_no_risk(self) -> None:
        summary, supports = self.collector._resolve_no_data_semantics(
            SimpleNamespace(rule_id="P001_FLEX_003")
        )

        self.assertTrue(supports)
        self.assertIn("未查询到身份切换记录", summary)

    def test_subsidy_history_no_data_is_treated_as_no_prior_claim(self) -> None:
        summary, supports = self.collector._resolve_no_data_semantics(
            SimpleNamespace(rule_id="P001_FLEX_005")
        )

        self.assertTrue(supports)
        self.assertIn("未查询到历史补贴领取记录", summary)

    def test_other_no_data_rules_keep_unknown_semantics(self) -> None:
        self.assertIsNone(
            self.collector._resolve_no_data_semantics(
                SimpleNamespace(rule_id="P001_FLEX_004")
            )
        )


if __name__ == "__main__":
    unittest.main()
