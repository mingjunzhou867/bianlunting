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

    def test_base_volatility_stable_is_neutral(self) -> None:
        summary, supports = self.collector._resolve_base_volatility_semantics(
            SimpleNamespace(rule_id="P001_FLEX_004"),
            [
                {"pay_month": "2026-01", "pay_base": 4000},
                {"pay_month": "2026-02", "pay_base": 4000},
            ],
        )

        self.assertIsNone(supports)
        self.assertIn("整体稳定", summary)
        self.assertIn("不构成负面证据", summary)

    def test_base_volatility_small_change_is_neutral(self) -> None:
        summary, supports = self.collector._resolve_base_volatility_semantics(
            SimpleNamespace(rule_id="P001_FLEX_004"),
            [
                {"pay_month": "2026-01", "pay_base": 4000},
                {"pay_month": "2026-02", "pay_base": 4200},
            ],
        )

        self.assertIsNone(supports)
        self.assertIn("轻微波动", summary)
        self.assertIn("不足以认定为异常风险", summary)

    def test_base_volatility_large_change_requires_review_but_not_fail(self) -> None:
        summary, supports = self.collector._resolve_base_volatility_semantics(
            SimpleNamespace(rule_id="P001_FLEX_004"),
            [
                {"pay_month": "2026-01", "pay_base": 5000},
                {"pay_month": "2026-02", "pay_base": 3000},
            ],
        )

        self.assertIsNone(supports)
        self.assertIn("较明显波动", summary)
        self.assertIn("不单独直接否决资格", summary)


if __name__ == "__main__":
    unittest.main()
