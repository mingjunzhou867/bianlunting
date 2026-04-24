"""Shared base utilities for debate agents."""
from __future__ import annotations

import ast
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, get_args

from loguru import logger
from pydantic import BaseModel, Field

from config.llm_client import llm_chat
from config.settings import settings
from evidence.evidence_model import EvidenceBundle
from evidence.evidence_projection import EvidenceProjection


CONCLUSION_PASS = "符合"
CONCLUSION_FAIL = "不符合"
CONCLUSION_MISSING = "数据缺失"

STANCE_SUPPORT = "支持通过"
STANCE_OPPOSE = "反对通过"
STANCE_PENDING = "待定"

LEGACY_CONCLUSION_ALIASES = {
    CONCLUSION_PASS: {CONCLUSION_PASS, "绗﹀悎", "缁楋箑鎮?", "閺€顖涘瘮", STANCE_SUPPORT, "鏀寔閫氳繃"},
    CONCLUSION_FAIL: {CONCLUSION_FAIL, "涓嶇鍚?", "娑撳秶顑侀崥", "閸欏秴顕?", STANCE_OPPOSE, "鍙嶅閫氳繃"},
    CONCLUSION_MISSING: {CONCLUSION_MISSING, "鏁版嵁缂哄け", "閺佺増宓佺紓鍝勩亼", "瀵板懎鐣?", STANCE_PENDING, "寰呭畾"},
}

LEGACY_STANCE_ALIASES = {
    STANCE_SUPPORT: {STANCE_SUPPORT, "鏀寔閫氳繃", "閺€顖涘瘮闁俺绻?", CONCLUSION_PASS, "绗﹀悎"},
    STANCE_OPPOSE: {STANCE_OPPOSE, "鍙嶅閫氳繃", "閸欏秴顕柅姘崇箖", CONCLUSION_FAIL, "涓嶇鍚?"},
    STANCE_PENDING: {STANCE_PENDING, "寰呭畾", "瀵板懎鐣?", CONCLUSION_MISSING, "鏁版嵁缂哄け"},
}

SHARED_CONTEXT = """
你正在参与“灵活就业社保补贴资格认定”的多 Agent 讨论。
你只能基于提供给你的证据做判断，不得虚构数据库事实。
最终输出必须是单个 JSON 对象，字段必须完整，且不得输出代码块或额外解释。
""".strip()


@dataclass(frozen=True)
class DebateToolPolicy:
    """Compatibility policy holder for debate tool usage."""

    allow_tools: bool = True
    require_existing_evidence_first: bool = True
    max_tool_calls_per_turn: int = 1
    allowed_tool_names: tuple[str, ...] = ("get_dict", "text_to_sql")


class AgentJudgment(BaseModel):
    """Normalized agent output used by orchestration and persistence."""

    agent_id: str = Field(description="Agent id")
    agent_role: str = Field(description="Agent role")
    debate_round: int = Field(default=0, description="Debate round number")
    conclusion: Literal[CONCLUSION_PASS, CONCLUSION_FAIL, CONCLUSION_MISSING] = Field(
        description="Final conclusion"
    )
    stance: Literal[STANCE_SUPPORT, STANCE_OPPOSE, STANCE_PENDING] = Field(
        description="Voting stance"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    evidence_refs: list[str] = Field(default_factory=list, description="Evidence refs")
    reasoning: str = Field(description="Reasoning text")
    dissent_points: list[str] = Field(default_factory=list, description="Dissent points")
    key_finding: str = Field(default="", description="Most important finding")


def format_evidence_bundle(bundle: EvidenceBundle) -> str:
    """Render the legacy bundle format for prompt comparison/regression."""

    lines = [f"【取证对象】{bundle.id_card}", ""]
    support_labels = {
        True: STANCE_SUPPORT,
        False: STANCE_OPPOSE,
        None: "需 Agent 判断",
    }

    for item in bundle.items:
        lines.append(f"[{item.rule_id}] {item.target}")
        lines.append(
            f"  类别: {item.category} | 状态: {item.exec_status} | 结论: {support_labels[item.supports_conclusion]}"
        )
        lines.append(f"  摘要: {item.result_summary}")
        lines.append("")

    return "\n".join(lines)


def format_projection(projection: EvidenceProjection) -> str:
    """Render the projection format consumed by debate agents."""

    status_labels = {
        "supports": STANCE_SUPPORT,
        "contradicts": STANCE_OPPOSE,
        "unresolved": "需 Agent 判断",
        "missing": "证据缺失",
    }

    lines = [
        f"【任务】{projection.task_header}",
        f"【取证对象】{projection.target_person}",
        f"【政策范围】{projection.policy_scope}",
        (
            f"【证据概览】共 {projection.total_cards} 项证据，"
            f"已确认 {projection.resolved_count} 项，"
            f"待确认 {projection.unresolved_count} 项"
        ),
        "",
    ]

    for card in projection.cards:
        lines.append(f"[{card.card_id}] {card.question}")
        lines.append(
            "  "
            f"{status_labels.get(card.status, card.status)}"
            f" | {card.confidence:.0%}"
            f" | {', '.join(card.artifact_refs)}"
        )
        lines.append(f"  {card.finding}")
        lines.append("")

    if projection.uncertainty_markers:
        lines.append("【不确定性标记】")
        for marker in projection.uncertainty_markers:
            lines.append(f"  - {marker}")
        lines.append("")

    return "\n".join(lines)


def format_persona_context(persona_context: dict | None) -> str:
    """Render compact persona context for pre-debate grounding."""
    if not isinstance(persona_context, dict) or not persona_context:
        return ""

    lines: list[str] = ["【用户画像】"]
    title = str(persona_context.get("title") or "").strip()
    archetype = str(persona_context.get("archetype") or "").strip()
    summary_line = str(persona_context.get("summary_line") or "").strip()
    core_intent = str(persona_context.get("core_intent") or "").strip()
    substantive_dispute = str(persona_context.get("substantive_dispute") or "").strip()
    risk_level = str(persona_context.get("risk_level") or "").strip()

    if title:
        lines.append(f"- 标题: {title}")
    if archetype:
        lines.append(f"- 原型: {archetype}")
    if summary_line:
        lines.append(f"- 摘要: {summary_line}")
    if core_intent:
        lines.append(f"- 核心意图: {core_intent}")
    if substantive_dispute:
        lines.append(f"- 实质争议: {substantive_dispute}")
    if risk_level:
        lines.append(f"- 风险级别: {risk_level}")

    dispute_points = persona_context.get("dispute_points")
    if isinstance(dispute_points, list) and dispute_points:
        lines.append("- 辩论焦点:")
        for point in dispute_points[:4]:
            point_text = str(point).strip()
            if point_text:
                lines.append(f"  * {point_text}")

    return "\n".join(lines)


class BaseAgent(ABC):
    """Abstract base class for all debate agents."""

    AGENT_ID: str = "base"
    AGENT_ROLE: str = "基础 Agent"
    TEMPERATURE: float = 0.3
    MIN_REASONING_CHARS: int = 30

    _STANCE_BY_CONCLUSION = {
        CONCLUSION_PASS: STANCE_SUPPORT,
        CONCLUSION_FAIL: STANCE_OPPOSE,
        CONCLUSION_MISSING: STANCE_PENDING,
    }

    @property
    @abstractmethod
    def SYSTEM_PROMPT(self) -> str:
        ...

    def judge(
        self,
        projection: EvidenceProjection,
        debate_round: int = 0,
        case_summaries: list[dict] | None = None,
        persona_context: dict | None = None,
        tools: list[dict] | None = None,
        tool_registry=None,
        tool_policy: DebateToolPolicy | None = None,
    ) -> AgentJudgment:
        evidence_text = format_projection(projection)
        persona_text = format_persona_context(persona_context)
        user_content = evidence_text
        if persona_text:
            user_content = f"{user_content}\n\n{persona_text}"
        user_content = f"{user_content}\n\n请基于以上证据按约定 JSON 格式输出你的判断。"

        if tools and tool_registry and (tool_policy is None or tool_policy.allow_tools):
            raw = self._call_llm_with_tools(self.SYSTEM_PROMPT, user_content, tools, tool_registry)
        else:
            raw = self._call_llm(self.SYSTEM_PROMPT, user_content)
        raw = self._ensure_structured_judgment_output(raw, self.SYSTEM_PROMPT)

        judgment = self._parse_judgment(raw)
        judgment = self._postprocess_judgment(judgment, projection)
        judgment.debate_round = debate_round
        return judgment

    def debate_respond(
        self,
        projection: EvidenceProjection,
        previous_judgments: list[AgentJudgment],
        debate_round: int = 1,
        case_summaries: list[dict] | None = None,
        persona_context: dict | None = None,
        tools: list[dict] | None = None,
        tool_registry=None,
        tool_policy: DebateToolPolicy | None = None,
    ) -> AgentJudgment:
        evidence_text = format_projection(projection)
        persona_text = format_persona_context(persona_context)
        other_views = self._format_other_judgments(previous_judgments)
        user_content = evidence_text
        if persona_text:
            user_content = f"{user_content}\n\n{persona_text}"
        user_content = (
            f"{user_content}\n\n"
            f"【其他 Agent 的判断】\n{other_views}\n\n"
            "请结合当前证据和其他 Agent 观点，按约定 JSON 格式输出你的回应。"
        )

        if tools and tool_registry and (tool_policy is None or tool_policy.allow_tools):
            raw = self._call_llm_with_tools(self.SYSTEM_PROMPT, user_content, tools, tool_registry)
        else:
            raw = self._call_llm(
                self.SYSTEM_PROMPT,
                user_content,
                temperature=self.TEMPERATURE + 0.1,
            )
        raw = self._ensure_structured_judgment_output(raw, self.SYSTEM_PROMPT)

        judgment = self._parse_judgment(raw)
        judgment = self._postprocess_judgment(judgment, projection)
        judgment.debate_round = debate_round
        return judgment

    def _postprocess_judgment(
        self,
        judgment: AgentJudgment,
        projection: EvidenceProjection,
    ) -> AgentJudgment:
        expected_stance = self._STANCE_BY_CONCLUSION.get(judgment.conclusion)
        if expected_stance and judgment.stance != expected_stance:
            logger.warning(
                "[{}] normalize stance from conclusion: {} -> {}",
                self.AGENT_ID,
                judgment.stance,
                expected_stance,
            )
            judgment.stance = expected_stance

        # Keep agent conclusion unchanged here to avoid repeated adjudication in
        # agent post-processing, round aggregation, and final reports.
        judgment.confidence = max(0.0, min(1.0, float(judgment.confidence)))

        return judgment

    def _call_llm(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float | None = None,
    ) -> str:
        full_system = f"{SHARED_CONTEXT}\n\n{system_prompt}"
        reply = llm_chat(
            system_prompt=full_system,
            user_message=user_content,
            temperature=temperature if temperature is not None else self.TEMPERATURE,
            response_format=self._judgment_response_format() if settings.use_openai_compat else None,
        )
        if not isinstance(reply, str):
            reply = json.dumps(reply, ensure_ascii=False)
        logger.debug("[{}] LLM reply length: {}", self.AGENT_ID, len(reply))
        return reply

    def _judgment_schema(self) -> dict:
        conclusion_enum = list(get_args(AgentJudgment.model_fields["conclusion"].annotation))
        stance_enum = list(get_args(AgentJudgment.model_fields["stance"].annotation))
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "conclusion",
                "stance",
                "confidence",
                "evidence_refs",
                "reasoning",
                "dissent_points",
                "key_finding",
            ],
            "properties": {
                "conclusion": {"type": "string", "enum": conclusion_enum},
                "stance": {"type": "string", "enum": stance_enum},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string", "minLength": self.MIN_REASONING_CHARS},
                "dissent_points": {"type": "array", "items": {"type": "string"}},
                "key_finding": {"type": "string"},
            },
        }

    def _judgment_response_format(self) -> dict:
        if settings.llm_provider in {"dashscope", "zhipu", "nova", "deepseek"}:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": f"{self.AGENT_ID}_judgment",
                "strict": True,
                "schema": self._judgment_schema(),
            },
        }

    def _canonical_conclusion(self, value: object) -> str:
        valid = tuple(get_args(AgentJudgment.model_fields["conclusion"].annotation))
        text = self._normalize_text(value)
        if text in valid:
            return text

        lowered = text.lower()
        if self._contains_alias(text, LEGACY_CONCLUSION_ALIASES[CONCLUSION_FAIL]) or "reject" in lowered or "fail" in lowered:
            return valid[1]
        if self._contains_alias(text, LEGACY_CONCLUSION_ALIASES[CONCLUSION_PASS]) or "approve" in lowered or "pass" in lowered:
            return valid[0]
        if self._contains_alias(text, LEGACY_CONCLUSION_ALIASES[CONCLUSION_MISSING]) or "missing" in lowered or "unknown" in lowered:
            return valid[2]
        return valid[2]

    def _canonical_stance(self, value: object) -> str:
        valid = tuple(get_args(AgentJudgment.model_fields["stance"].annotation))
        text = self._normalize_text(value)
        if text in valid:
            return text

        lowered = text.lower()
        if self._contains_alias(text, LEGACY_STANCE_ALIASES[STANCE_OPPOSE]) or "reject" in lowered or "oppose" in lowered:
            return valid[1]
        if self._contains_alias(text, LEGACY_STANCE_ALIASES[STANCE_SUPPORT]) or "support" in lowered or "approve" in lowered:
            return valid[0]
        if self._contains_alias(text, LEGACY_STANCE_ALIASES[STANCE_PENDING]) or "pending" in lowered or "unknown" in lowered:
            return valid[2]
        return valid[2]

    def _contains_alias(self, text: str, aliases: set[str]) -> bool:
        compact = text.replace(" ", "")
        return any(alias and alias in compact for alias in aliases)

    def _try_parse_judgment_payload(self, raw: str) -> dict | None:
        if not raw or not isinstance(raw, str):
            return None
        try:
            payload = self._load_judgment_payload(self._extract_json(raw))
            return self._normalize_judgment_payload(payload)
        except Exception:
            return None

    def _is_valid_judgment_payload(self, payload: dict | None) -> bool:
        if not isinstance(payload, dict):
            return False
        required_keys = {
            "conclusion",
            "stance",
            "confidence",
            "evidence_refs",
            "reasoning",
            "dissent_points",
            "key_finding",
        }
        if not required_keys.issubset(payload.keys()):
            return False

        conclusion_enum = set(get_args(AgentJudgment.model_fields["conclusion"].annotation))
        stance_enum = set(get_args(AgentJudgment.model_fields["stance"].annotation))
        payload["conclusion"] = self._canonical_conclusion(payload.get("conclusion"))
        payload["stance"] = self._canonical_stance(payload.get("stance"))
        if payload.get("conclusion") not in conclusion_enum:
            return False
        if payload.get("stance") not in stance_enum:
            return False

        try:
            confidence = float(payload.get("confidence"))
        except (TypeError, ValueError):
            return False
        if confidence < 0 or confidence > 1:
            return False

        if not isinstance(payload.get("evidence_refs"), list):
            return False
        if not isinstance(payload.get("dissent_points"), list):
            return False
        if not isinstance(payload.get("reasoning"), str):
            return False
        if len(payload.get("reasoning", "").strip()) < self.MIN_REASONING_CHARS:
            return False
        if not isinstance(payload.get("key_finding"), str):
            return False
        return True

    def _describe_invalid_judgment_payload(self, raw: str) -> str:
        if not raw or not isinstance(raw, str) or not raw.strip():
            return "empty_response"

        payload = self._try_parse_judgment_payload(raw)
        if not isinstance(payload, dict):
            return "json_extract_failed"

        required_keys = (
            "conclusion",
            "stance",
            "confidence",
            "evidence_refs",
            "reasoning",
            "dissent_points",
            "key_finding",
        )
        missing_keys = [key for key in required_keys if key not in payload]
        if missing_keys:
            return f"missing_keys={','.join(missing_keys)}"

        conclusion = self._canonical_conclusion(payload.get("conclusion"))
        conclusion_enum = set(get_args(AgentJudgment.model_fields["conclusion"].annotation))
        if conclusion not in conclusion_enum:
            return f"invalid_conclusion={self._normalize_text(payload.get('conclusion'))!r}"

        stance = self._canonical_stance(payload.get("stance"))
        stance_enum = set(get_args(AgentJudgment.model_fields["stance"].annotation))
        if stance not in stance_enum:
            return f"invalid_stance={self._normalize_text(payload.get('stance'))!r}"

        try:
            confidence = float(payload.get("confidence"))
        except (TypeError, ValueError):
            return f"invalid_confidence={payload.get('confidence')!r}"
        if confidence < 0 or confidence > 1:
            return f"confidence_out_of_range={confidence!r}"

        if not isinstance(payload.get("evidence_refs"), list):
            return f"invalid_evidence_refs_type={type(payload.get('evidence_refs')).__name__}"
        if not isinstance(payload.get("dissent_points"), list):
            return f"invalid_dissent_points_type={type(payload.get('dissent_points')).__name__}"
        if not isinstance(payload.get("reasoning"), str):
            return f"invalid_reasoning_type={type(payload.get('reasoning')).__name__}"

        reasoning = payload.get("reasoning", "").strip()
        if len(reasoning) < self.MIN_REASONING_CHARS:
            return f"reasoning_too_short={len(reasoning)}<{self.MIN_REASONING_CHARS}"

        if not isinstance(payload.get("key_finding"), str):
            return f"invalid_key_finding_type={type(payload.get('key_finding')).__name__}"
        return "unknown_contract_violation"

    def _preview_raw_output(self, raw: str, limit: int = 240) -> str:
        if not isinstance(raw, str):
            return repr(raw)
        compact = raw.strip().replace("\r", "\\r").replace("\n", "\\n")
        if len(compact) <= limit:
            return compact
        return compact[:limit] + "...(truncated)"

    def _ensure_structured_judgment_output(
        self,
        raw: str,
        system_prompt: str,
        retries: int = 3,
    ) -> str:
        payload = self._try_parse_judgment_payload(raw)
        if self._is_valid_judgment_payload(payload):
            return raw

        logger.warning(
            "[{}] Non-structured judgment output, entering repair flow: reason={} raw={}",
            self.AGENT_ID,
            self._describe_invalid_judgment_payload(raw),
            self._preview_raw_output(raw),
        )
        current_raw = raw
        for attempt in range(1, retries + 1):
            repair_system = f"{SHARED_CONTEXT}\n\n{system_prompt}"
            repair_user = (
                "上一条回答不符合 JSON 契约。\n"
                "请严格按约定字段输出单个 JSON 对象，不要代码块，不要额外解释。\n"
                "必须且只允许包含这些字段："
                "conclusion, stance, confidence, evidence_refs, reasoning, dissent_points, key_finding。\n"
                f"conclusion 只能是：{CONCLUSION_PASS} / {CONCLUSION_FAIL} / {CONCLUSION_MISSING}。\n"
                f"stance 只能是：{STANCE_SUPPORT} / {STANCE_OPPOSE} / {STANCE_PENDING}。\n"
                "evidence_refs 和 dissent_points 必须是字符串数组；如无内容必须输出 []。\n"
                f"reasoning 必须是可读文本，且不少于 {self.MIN_REASONING_CHARS} 个字。\n"
                f"原始输出：\n{current_raw}"
            )
            repaired = llm_chat(
                system_prompt=repair_system,
                user_message=repair_user,
                temperature=0.0,
                response_format=self._judgment_response_format() if settings.use_openai_compat else None,
            )
            if not isinstance(repaired, str):
                repaired = json.dumps(repaired, ensure_ascii=False)
            payload = self._try_parse_judgment_payload(repaired)
            if self._is_valid_judgment_payload(payload):
                logger.warning("[{}] Structured output repaired on attempt {}", self.AGENT_ID, attempt)
                return repaired
            logger.warning(
                "[{}] Repair attempt {} still invalid: reason={} raw={}",
                self.AGENT_ID,
                attempt,
                self._describe_invalid_judgment_payload(repaired),
                self._preview_raw_output(repaired),
            )
            current_raw = repaired

        logger.error(
            "[{}] Structured output repair failed after {} attempts: reason={} raw={}",
            self.AGENT_ID,
            retries,
            self._describe_invalid_judgment_payload(current_raw),
            self._preview_raw_output(current_raw),
        )
        fallback_payload = self._build_fallback_payload(current_raw)
        return json.dumps(fallback_payload, ensure_ascii=False)

    def _build_fallback_payload(self, raw: str) -> dict:
        inferred = self._infer_payload_from_text(raw)
        conclusion = self._canonical_conclusion(inferred.get("conclusion"))
        stance = self._canonical_stance(inferred.get("stance"))
        confidence = float(inferred.get("confidence", 0.3))
        reasoning = inferred.get("reasoning") or "模型未返回可读推理，已按保守策略生成结构化结论。"
        key_finding = inferred.get("key_finding") or "推理文本缺失"
        reasoning = self._ensure_min_reasoning_length(reasoning)

        return {
            "conclusion": conclusion,
            "stance": stance,
            "confidence": max(0.0, min(1.0, confidence)),
            "evidence_refs": [],
            "reasoning": reasoning,
            "dissent_points": ["模型未返回可读推理文本"],
            "key_finding": key_finding,
        }

    def _call_llm_with_tools(
        self,
        system_prompt: str,
        user_content: str,
        tools: list[dict],
        tool_registry,
        max_iterations: int = 3,
    ) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.get_effective_base_url() or None,
        )
        full_system = (
            f"{SHARED_CONTEXT}\n\n{system_prompt}\n\n"
            "你可以调用工具查询数据库获取更多信息。"
            "如果已有信息足够，可以直接输出最终 JSON 判断。"
        )

        messages: list[dict] = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_content},
        ]
        response_format = self._judgment_response_format() if settings.use_openai_compat else None

        for iteration in range(max_iterations):
            resp = self._create_completion(
                client,
                messages=messages,
                temperature=self.TEMPERATURE,
                tools=tools,
                response_format=response_format,
            )
            msg = resp.choices[0].message

            if not msg.tool_calls:
                content = msg.content or ""
                logger.debug(
                    "[{}] tool-loop finished after {} iter, reply len={}",
                    self.AGENT_ID,
                    iteration + 1,
                    len(content),
                )
                return content

            messages.append(msg.model_dump(exclude_unset=True))
            for tc in msg.tool_calls:
                try:
                    result = tool_registry.execute(tc.function.name, json.loads(tc.function.arguments))
                except Exception as tool_exc:
                    result = f"工具执行出错: {tool_exc}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result),
                    }
                )
            logger.debug(
                "[{}] tool-loop iter={} called {} tools",
                self.AGENT_ID,
                iteration + 1,
                len(msg.tool_calls),
            )

        logger.warning("[{}] tool-loop hit max_iterations={}, forcing final answer", self.AGENT_ID, max_iterations)
        messages.append(
            {
                "role": "user",
                "content": "请不要再调用工具，直接基于现有信息按 JSON 格式输出最终判断。",
            }
        )
        final_resp = self._create_completion(
            client,
            messages=messages,
            temperature=self.TEMPERATURE,
            response_format=response_format,
        )
        return final_resp.choices[0].message.content or ""

    def _create_completion(
        self,
        client,
        *,
        messages: list[dict],
        temperature: float,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ):
        kwargs = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
        if response_format:
            kwargs["response_format"] = response_format
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            if tools and response_format:
                logger.warning(
                    "[{}] tool call request rejected with response_format, retrying without it: {}",
                    self.AGENT_ID,
                    exc,
                )
                retry_kwargs = dict(kwargs)
                retry_kwargs.pop("response_format", None)
                return client.chat.completions.create(**retry_kwargs)
            raise

    def _parse_judgment(self, raw: str) -> AgentJudgment:
        if not raw or not raw.strip():
            logger.warning("[{}] LLM returned empty content, using fallback judgment", self.AGENT_ID)
            return AgentJudgment(
                agent_id=self.AGENT_ID,
                agent_role=self.AGENT_ROLE,
                conclusion=CONCLUSION_MISSING,
                stance=STANCE_PENDING,
                confidence=0.0,
                evidence_refs=[],
                reasoning="LLM 返回空内容，可能是工具调用循环未收敛。",
                dissent_points=["LLM 输出为空"],
                key_finding="输出为空",
            )

        json_str = self._extract_json(raw)
        try:
            data = self._load_judgment_payload(json_str)
            data = self._normalize_judgment_payload(data)
            data = self._merge_with_inferred_if_sparse(data, raw)
            return AgentJudgment(
                agent_id=self.AGENT_ID,
                agent_role=self.AGENT_ROLE,
                conclusion=self._canonical_conclusion(data.get("conclusion")),
                stance=self._canonical_stance(data.get("stance")),
                confidence=float(data.get("confidence", 0.5)),
                evidence_refs=self._normalize_string_list(data.get("evidence_refs", [])),
                reasoning=self._normalize_reasoning_safe(data.get("reasoning", ""), raw),
                dissent_points=self._normalize_string_list(data.get("dissent_points", [])),
                key_finding=self._normalize_text(data.get("key_finding", "")),
            )
        except Exception as exc:
            logger.warning(
                "[{}] Judgment JSON parse failed: {} | raw[:200]={!r}",
                self.AGENT_ID,
                exc,
                raw[:200],
            )
            inferred = self._infer_payload_from_text(raw)
            return AgentJudgment(
                agent_id=self.AGENT_ID,
                agent_role=self.AGENT_ROLE,
                conclusion=self._canonical_conclusion(inferred.get("conclusion")),
                stance=self._canonical_stance(inferred.get("stance")),
                confidence=float(inferred.get("confidence", 0.3)),
                evidence_refs=[],
                reasoning=inferred.get("reasoning") or "LLM reasoning missing; parsing fallback applied",
                dissent_points=["LLM 输出不是有效 JSON"],
                key_finding=inferred.get("key_finding", "解析失败"),
            )

    def _extract_json(self, text: str) -> str:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return fenced.group(1)

        block = re.search(r"\{.*\}", text, re.DOTALL)
        if block:
            return block.group(0)

        return text

    def _load_judgment_payload(self, text: str) -> dict:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        try:
            data = ast.literal_eval(text)
            if isinstance(data, dict):
                return data
        except (ValueError, SyntaxError):
            pass

        repaired = self._repair_json_like(text)
        try:
            data = json.loads(repaired)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        try:
            data = ast.literal_eval(repaired)
            if isinstance(data, dict):
                return data
        except (ValueError, SyntaxError):
            pass

        raise ValueError("LLM output is not a valid JSON object")

    def _normalize_judgment_payload(self, payload: dict | None) -> dict | None:
        if not isinstance(payload, dict):
            return payload

        normalized = dict(payload)
        for key in ("evidence_refs", "dissent_points"):
            if normalized.get(key) == "":
                normalized[key] = []
        return normalized

    def _repair_json_like(self, text: str) -> str:
        repaired = text.strip()
        repaired = re.sub(r"^```(?:json)?\s*", "", repaired, flags=re.IGNORECASE)
        repaired = re.sub(r"\s*```$", "", repaired)
        repaired = repaired.replace("“", "\"").replace("”", "\"")
        repaired = repaired.replace("‘", "'").replace("’", "'")
        repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
        repaired = re.sub(r"\bNone\b", "null", repaired)
        repaired = re.sub(r"\bTrue\b", "true", repaired)
        repaired = re.sub(r"\bFalse\b", "false", repaired)
        return repaired

    def _normalize_reasoning(self, value: object, raw: str) -> str:
        text = self._normalize_text(value)
        if text:
            return text
        return f"LLM 未返回 reasoning 字段，原始片段: {raw[:200]}"

    def _normalize_text(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def _normalize_string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            normalized_items: list[str] = []
            for item in value:
                if isinstance(item, (dict, list, tuple, set)):
                    continue
                text = self._normalize_text(item)
                if text:
                    normalized_items.append(text)
            return normalized_items

        if isinstance(value, (dict, tuple, set)):
            return []
        text = self._normalize_text(value)
        return [text] if text else []

    def _merge_with_inferred_if_sparse(self, data: dict, raw: str) -> dict:
        """Use natural-language hints when the JSON payload is sparse."""

        inferred = self._infer_payload_from_text(raw)
        merged = dict(data or {})
        for key in ("conclusion", "stance", "confidence", "reasoning", "key_finding"):
            value = merged.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                if key in inferred:
                    merged[key] = inferred[key]
        return merged

    def _infer_payload_from_text(self, raw: str) -> dict[str, object]:
        text = self._extract_human_reasoning(raw)
        if not text:
            text = self._sanitize_reasoning_text(self._strip_code_fences(raw).strip())
        if not text:
            return {
                "reasoning": "模型未返回可读推理，已使用保守兜底策略。",
                "key_finding": "推理文本缺失",
            }

        conclusion = CONCLUSION_MISSING
        lowered = text.lower()
        if self._contains_alias(text, LEGACY_CONCLUSION_ALIASES[CONCLUSION_FAIL]) or "reject" in lowered:
            conclusion = CONCLUSION_FAIL
        elif self._contains_alias(text, LEGACY_CONCLUSION_ALIASES[CONCLUSION_PASS]) or "approve" in lowered:
            conclusion = CONCLUSION_PASS
        elif self._contains_alias(text, LEGACY_CONCLUSION_ALIASES[CONCLUSION_MISSING]) or "missing" in lowered:
            conclusion = CONCLUSION_MISSING

        stance_map = {
            CONCLUSION_PASS: STANCE_SUPPORT,
            CONCLUSION_FAIL: STANCE_OPPOSE,
            CONCLUSION_MISSING: STANCE_PENDING,
        }
        return {
            "conclusion": conclusion,
            "stance": stance_map[conclusion],
            "confidence": 0.55 if conclusion != CONCLUSION_MISSING else 0.45,
            "reasoning": self._ensure_min_reasoning_length(text[:500]),
            "key_finding": text[:80],
        }

    def _strip_code_fences(self, text: str) -> str:
        stripped = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
        stripped = stripped.replace("```", "")
        return stripped

    def _normalize_reasoning_safe(self, value: object, raw: str) -> str:
        text = self._normalize_text(value)
        cleaned = self._sanitize_reasoning_text(text)
        if cleaned:
            return cleaned

        inferred = self._extract_human_reasoning(raw)
        if inferred:
            return inferred

        return "模型未返回可读推理，已使用保守兜底策略。"

    def _ensure_min_reasoning_length(self, text: str) -> str:
        base = (text or "").strip()
        if len(base) >= self.MIN_REASONING_CHARS:
            return base
        padding = " 已依据现有证据按保守原则生成结论，并建议人工复核关键争议点。"
        while len(base) < self.MIN_REASONING_CHARS:
            base = (base + padding).strip()
        return base[:500]

    def _extract_human_reasoning(self, raw: str) -> str:
        text = raw or ""
        if not text:
            return ""

        if "{" in text:
            prefix = text.split("{", 1)[0].strip()
            prefix = self._sanitize_reasoning_text(prefix)
            if prefix:
                return prefix

        text = re.sub(r"```(?:json)?[\s\S]*?```", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\{[\s\S]*\}", " ", text)
        return self._sanitize_reasoning_text(text)

    def _sanitize_reasoning_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = self._strip_code_fences(text).strip()
        if not cleaned:
            return ""
        cleaned = re.sub(r"\s+", " ", cleaned)
        if self._looks_like_json_blob(cleaned):
            return ""
        return cleaned[:500]

    def _looks_like_json_blob(self, text: str) -> bool:
        candidate = text.strip()
        if not candidate:
            return False
        if candidate.startswith("{") or candidate.startswith("["):
            return True
        if '"conclusion"' in candidate or '"stance"' in candidate or '"reasoning"' in candidate:
            return True
        if candidate.count("{") >= 2 and candidate.count("}") >= 2 and ":" in candidate:
            return True
        return False

    def _format_other_judgments(self, judgments: list[AgentJudgment]) -> str:
        lines: list[str] = []
        for judgment in judgments:
            if judgment.agent_id == self.AGENT_ID:
                continue
            lines.append(
                f"- {judgment.agent_role}（置信度 {judgment.confidence:.0%}）："
                f"{judgment.conclusion} / {judgment.stance}"
            )
            lines.append(f"  推理：{judgment.reasoning}")
            if judgment.dissent_points:
                lines.append(f"  质疑：{';'.join(judgment.dissent_points)}")
        return "\n".join(lines) if lines else "（本轮无其他 Agent 发言）"
