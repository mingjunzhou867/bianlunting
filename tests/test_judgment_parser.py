from __future__ import annotations

import unittest
from typing import get_args

from agents.base_agent import AgentJudgment, BaseAgent


class _DummyAgent(BaseAgent):
    AGENT_ID = "dummy_agent"
    AGENT_ROLE = "DummyAgent"

    @property
    def SYSTEM_PROMPT(self) -> str:
        return "dummy"


class JudgmentParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = _DummyAgent()
        conclusion_enum = get_args(AgentJudgment.model_fields["conclusion"].annotation)
        stance_enum = get_args(AgentJudgment.model_fields["stance"].annotation)
        self.pass_conclusion = conclusion_enum[0]
        self.fail_conclusion = conclusion_enum[1]
        self.support_stance = stance_enum[0]
        self.oppose_stance = stance_enum[1]

    def test_infer_from_plain_text_with_incomplete_json_fence(self) -> None:
        raw = f"根据证据综合判断，申请人条件{self.pass_conclusion}政策要求。\n\n```json\n"
        judgment = self.agent._parse_judgment(raw)

        self.assertEqual(judgment.conclusion, self.pass_conclusion)
        self.assertEqual(judgment.stance, self.support_stance)
        self.assertTrue(judgment.reasoning)

    def test_filter_non_string_entries_in_list_fields(self) -> None:
        raw = f"""
{{
  "conclusion": "{self.pass_conclusion}",
  "stance": "{self.support_stance}",
  "confidence": 0.8,
  "reasoning": "现有证据整体支持通过，且理由文本长度足够满足结构化校验要求。",
  "evidence_refs": ["BASIC_001", {{}}, []],
  "dissent_points": ["需要补核社保月数", {{}}],
  "key_finding": "基础条件完整"
}}
"""
        judgment = self.agent._parse_judgment(raw)

        self.assertEqual(judgment.evidence_refs, ["BASIC_001"])
        self.assertEqual(judgment.dissent_points, ["需要补核社保月数"])

    def test_empty_string_dissent_points_is_normalized_to_empty_list(self) -> None:
        raw = f"""
{{
  "conclusion": "{self.fail_conclusion}",
  "stance": "{self.oppose_stance}",
  "confidence": 0.85,
  "reasoning": "关键证据缺失，且当前记录不足以证明申请人满足政策要求，因此不能直接通过。",
  "evidence_refs": [],
  "dissent_points": "",
  "key_finding": "关键证据缺失"
}}
"""
        judgment = self.agent._parse_judgment(raw)

        self.assertEqual(judgment.dissent_points, [])

    def test_parse_failure_does_not_echo_json_blob_in_reasoning(self) -> None:
        raw = "根据现有证据，申请人基本满足条件。\n```json\n{bad_json\n"
        judgment = self.agent._parse_judgment(raw)

        self.assertIn("根据现有证据", judgment.reasoning)
        self.assertNotIn("{bad_json", judgment.reasoning)

    def test_pure_json_failure_returns_sanitized_reasoning(self) -> None:
        raw = "{bad_json"
        judgment = self.agent._parse_judgment(raw)

        self.assertNotIn("{bad_json", judgment.reasoning)
        self.assertTrue(judgment.reasoning)


if __name__ == "__main__":
    unittest.main()
