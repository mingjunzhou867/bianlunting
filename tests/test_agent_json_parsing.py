from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from typing import get_args
from unittest.mock import patch

from agents.agent_explorer import ExploratoryAgent
from agents.base_agent import AgentJudgment, BaseAgent, DebateToolPolicy


class DummyAgent(BaseAgent):
    AGENT_ID = "dummy"
    AGENT_ROLE = "Dummy Agent"
    SYSTEM_PROMPT = "Return JSON only."


class AgentJsonParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = DummyAgent()
        conclusion_enum = get_args(AgentJudgment.model_fields["conclusion"].annotation)
        stance_enum = get_args(AgentJudgment.model_fields["stance"].annotation)
        self.valid_conclusion = conclusion_enum[0]
        self.valid_stance = stance_enum[0]
        self.fallback_conclusion = conclusion_enum[2]
        self.fallback_stance = stance_enum[2]
        self.long_reasoning = "现有证据链较完整，且推理文本长度足够满足结构化输出校验要求。"

    def test_parse_standard_json(self) -> None:
        raw = json.dumps(
            {
                "conclusion": self.valid_conclusion,
                "stance": self.valid_stance,
                "confidence": 0.91,
                "evidence_refs": ["RULE_001"],
                "reasoning": "standard-json",
                "dissent_points": [],
                "key_finding": "ok",
            },
            ensure_ascii=False,
        )

        judgment = self.agent._parse_judgment(raw)

        self.assertEqual(judgment.reasoning, "standard-json")
        self.assertEqual(judgment.evidence_refs, ["RULE_001"])
        self.assertEqual(judgment.key_finding, "ok")

    def test_parse_json_inside_code_fence_and_python_literals(self) -> None:
        raw = f"""```json
        {{
          'conclusion': '{self.valid_conclusion}',
          'stance': '{self.valid_stance}',
          'confidence': 0.88,
          'evidence_refs': 'RULE_002',
          'reasoning': 'python-literal',
          'dissent_points': None,
          'key_finding': 'repaired',
        }}
        ```"""

        judgment = self.agent._parse_judgment(raw)

        self.assertEqual(judgment.reasoning, "python-literal")
        self.assertEqual(judgment.evidence_refs, ["RULE_002"])
        self.assertEqual(judgment.dissent_points, [])
        self.assertEqual(judgment.key_finding, "repaired")

    def test_missing_reasoning_gets_fallback_text(self) -> None:
        raw = json.dumps(
            {
                "conclusion": self.fallback_conclusion,
                "stance": self.fallback_stance,
                "confidence": 0.2,
                "evidence_refs": [],
                "dissent_points": [],
                "key_finding": "",
            },
            ensure_ascii=False,
        )

        judgment = self.agent._parse_judgment(raw)

        self.assertTrue(judgment.reasoning)
        self.assertNotEqual(judgment.reasoning, judgment.key_finding)

    def test_payload_contract_validator_accepts_complete_payload(self) -> None:
        payload = {
            "conclusion": self.valid_conclusion,
            "stance": self.valid_stance,
            "confidence": 0.88,
            "evidence_refs": ["RULE_001"],
            "reasoning": self.long_reasoning,
            "dissent_points": [],
            "key_finding": "ok",
        }
        self.assertTrue(self.agent._is_valid_judgment_payload(payload))

    def test_payload_contract_validator_rejects_incomplete_payload(self) -> None:
        payload = {
            "conclusion": self.valid_conclusion,
            "stance": self.valid_stance,
            "confidence": 0.88,
            "reasoning": "missing arrays and key finding",
        }
        self.assertFalse(self.agent._is_valid_judgment_payload(payload))

    def test_payload_contract_validator_accepts_legacy_mojibake_enums(self) -> None:
        payload = {
            "conclusion": "绗﹀悎",
            "stance": "鏀寔閫氳繃",
            "confidence": 0.88,
            "evidence_refs": [],
            "reasoning": self.long_reasoning,
            "dissent_points": [],
            "key_finding": "ok",
        }
        self.assertTrue(self.agent._is_valid_judgment_payload(payload))
        self.assertEqual(payload["conclusion"], "符合")
        self.assertEqual(payload["stance"], "支持通过")

    def test_payload_contract_validator_rejects_empty_reasoning(self) -> None:
        payload = {
            "conclusion": self.valid_conclusion,
            "stance": self.valid_stance,
            "confidence": 0.88,
            "evidence_refs": [],
            "reasoning": "   ",
            "dissent_points": [],
            "key_finding": "ok",
        }
        self.assertFalse(self.agent._is_valid_judgment_payload(payload))

    def test_payload_contract_validator_rejects_short_reasoning(self) -> None:
        payload = {
            "conclusion": self.valid_conclusion,
            "stance": self.valid_stance,
            "confidence": 0.88,
            "evidence_refs": [],
            "reasoning": "太短",
            "dissent_points": [],
            "key_finding": "ok",
        }
        self.assertFalse(self.agent._is_valid_judgment_payload(payload))

    def test_fallback_payload_uses_valid_enums(self) -> None:
        payload = self.agent._build_fallback_payload("{bad_json")
        self.assertIn(payload["conclusion"], get_args(AgentJudgment.model_fields["conclusion"].annotation))
        self.assertIn(payload["stance"], get_args(AgentJudgment.model_fields["stance"].annotation))

    def test_describe_invalid_payload_reports_missing_keys(self) -> None:
        reason = self.agent._describe_invalid_judgment_payload("{}")
        self.assertIn("missing_keys=", reason)
        self.assertIn("conclusion", reason)
        self.assertIn("reasoning", reason)

    def test_describe_invalid_payload_reports_short_reasoning(self) -> None:
        raw = json.dumps(
            {
                "conclusion": self.valid_conclusion,
                "stance": self.valid_stance,
                "confidence": 0.88,
                "evidence_refs": [],
                "reasoning": "太短",
                "dissent_points": [],
                "key_finding": "ok",
            },
            ensure_ascii=False,
        )
        self.assertEqual(
            self.agent._describe_invalid_judgment_payload(raw),
            "reasoning_too_short=2<30",
        )

    def test_try_parse_normalizes_empty_string_list_fields(self) -> None:
        raw = json.dumps(
            {
                "conclusion": self.valid_conclusion,
                "stance": self.valid_stance,
                "confidence": 0.88,
                "evidence_refs": "",
                "reasoning": self.long_reasoning,
                "dissent_points": "",
                "key_finding": "ok",
            },
            ensure_ascii=False,
        )
        payload = self.agent._try_parse_judgment_payload(raw)
        self.assertEqual(payload["evidence_refs"], [])
        self.assertEqual(payload["dissent_points"], [])

    def test_tool_path_uses_response_format_on_first_request(self) -> None:
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[], content="{}"))]
        )
        captured_calls: list[dict] = []

        def fake_create_completion(_self, _client, **kwargs):
            captured_calls.append(kwargs)
            return fake_response

        with patch("openai.OpenAI", return_value=SimpleNamespace()):
            with patch.object(DummyAgent, "_create_completion", autospec=True, side_effect=fake_create_completion):
                raw = self.agent._call_llm_with_tools(
                    self.agent.SYSTEM_PROMPT,
                    "请输出 JSON",
                    tools=[{"type": "function", "function": {"name": "noop", "parameters": {"type": "object"}}}],
                    tool_registry=SimpleNamespace(execute=lambda *_args, **_kwargs: {}),
                    tool_policy=DebateToolPolicy(allowed_tool_names=("noop",)),
                    max_iterations=1,
                )

        self.assertEqual(raw, "{}")
        self.assertEqual(captured_calls[0]["response_format"], self.agent._judgment_response_format())

    def test_filter_tools_by_policy_keeps_only_allowed_tools(self) -> None:
        tools = [
            {"type": "function", "function": {"name": "get_dict"}},
            {"type": "function", "function": {"name": "text_to_sql"}},
        ]

        filtered = self.agent._filter_tools_by_policy(
            tools,
            DebateToolPolicy(allowed_tool_names=("get_dict",)),
        )

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["function"]["name"], "get_dict")

    def test_tool_boundary_prompt_mentions_evidence_first_and_budget(self) -> None:
        prompt = self.agent._build_tool_boundary_prompt(
            DebateToolPolicy(max_tool_calls_per_turn=1, allowed_tool_names=("get_dict",))
        )

        self.assertIn("judge without tools if possible", prompt)
        self.assertIn("Max tool calls this turn: 1", prompt)


class ExplorerPromptContractTests(unittest.TestCase):
    def test_explorer_prompt_requires_numeric_confidence(self) -> None:
        prompt = ExploratoryAgent().SYSTEM_PROMPT
        self.assertIn("confidence", prompt)
        self.assertIn("0", prompt)
        self.assertIn("1", prompt)
        self.assertIn("number", prompt)


if __name__ == "__main__":
    unittest.main()
