"""
意图理解Agent - 将自然语言需求转换为结构化政策意图
"""
import json
import re
from typing import Dict, Any
from config.llm_client import llm_chat
from intent.models import PolicyIntent, CandidatePolicy
from loguru import logger
from policy.policy_router import list_policies


def _extract_json(text: str) -> str:
    """从LLM输出中提取JSON字符串"""
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def _normalize_action_type(value: Any) -> str:
    """Fallback for ambiguous LLM outputs where action_type may be null."""
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return "资格认定"


class IntentUnderstandingAgent:
    """
    意图理解Agent
    职责: 解析用户的自然语言需求,识别政策类型和行动类型
    """

    def __init__(self):
        self.system_prompt = self._build_system_prompt()
        self.temperature = 0.2

    def _build_system_prompt(self) -> str:
        """构建System Prompt（从数据库动态加载政策列表）"""
        policies = list_policies()

        policy_list_text = ""
        for idx, p in enumerate(policies, 1):
            policy_list_text += f"\n{idx}. **{p['policy_name']}** ({p['policy_id']})\n"
            policy_list_text += f"   - 政策类型: {p['policy_type']}\n"
            policy_list_text += f"   - 描述: {p['description']}\n"
            if p.get('keywords'):
                policy_list_text += f"   - 关键词: {', '.join(p['keywords'])}\n"

        return f"""你是一个政务政策意图理解专家。你的任务是将用户的自然语言需求转换为结构化的政策意图。

# 可用政策列表
{policy_list_text}

# 核心规则

**无论置信度高低，你必须始终输出全部{len(policies)}个政策的候选列表（candidate_policies），按 match_score 从高到低排列。**

match_score 取值范围 0.0~1.0 的浮点数，代表该政策与用户需求的匹配度（前端会乘以100显示为百分比）。

# 输出格式

你必须输出严格的JSON格式:

{{
  "policy_id": "最佳匹配的 policy_id，或 null",
  "policy_name": "最佳匹配的政策名称",
  "action_type": "资格认定 / 金额计算 / 历史查询 / 疑似人员识别",
  "confidence": 0.0~1.0 的浮点数,
  "reasoning": "你的推理过程",
  "ambiguities": ["歧义点1", "歧义点2"],
  "need_confirmation": true/false,
  "candidate_policies": [
    {{
      "policy_id": "POLICY_XXX",
      "policy_name": "...",
      "match_reason": "匹配原因（一句话）",
      "match_score": 0.0~1.0 的浮点数
    }}
  ]
}}

# 判断规则

1. **confidence >= 0.8**: 明确匹配到唯一政策, need_confirmation=false
2. **confidence 0.5~0.79**: 可能匹配多个政策, need_confirmation=true
3. **confidence < 0.5**: 无法识别, need_confirmation=true
"""

    def understand(self, user_query: str) -> PolicyIntent:
        """
        理解用户需求,返回结构化意图

        Args:
            user_query: 用户的自然语言需求

        Returns:
            PolicyIntent: 结构化的政策意图
        """
        logger.info(f"[IntentAgent] 开始解析用户需求: {user_query}")

        try:
            result_text = llm_chat(
                system_prompt=self.system_prompt,
                user_message=user_query,
                temperature=self.temperature
            )

            logger.debug(f"[IntentAgent] LLM原始输出: {result_text}")

            json_str = _extract_json(result_text)
            result = json.loads(json_str)

            intent = PolicyIntent(
                policy_id=result.get("policy_id"),
                policy_name=result.get("policy_name"),
                action_type=_normalize_action_type(result.get("action_type")),
                confidence=result.get("confidence", 0.0),
                reasoning=result.get("reasoning", ""),
                ambiguities=result.get("ambiguities", []),
                need_confirmation=result.get("need_confirmation", True),
                candidate_policies=[
                    CandidatePolicy(**cp) for cp in result.get("candidate_policies", [])
                ]
            )

            logger.info(f"[IntentAgent] 解析成功: policy_id={intent.policy_id}, confidence={intent.confidence}, need_confirmation={intent.need_confirmation}")
            return intent

        except json.JSONDecodeError as e:
            logger.error(f"[IntentAgent] JSON解析失败: {e}, 原始输出: {result_text}")
            return PolicyIntent(
                policy_id=None,
                policy_name=None,
                action_type="资格认定",
                confidence=0.0,
                reasoning=f"系统解析失败: {str(e)}",
                ambiguities=["系统无法理解您的需求,请重新描述"],
                need_confirmation=True,
                candidate_policies=[]
            )

        except Exception as e:
            logger.error(f"[IntentAgent] 意图理解失败: {e}")
            raise

    def batch_understand(self, queries: list[str]) -> list[PolicyIntent]:
        """
        批量理解多个用户需求

        Args:
            queries: 用户需求列表

        Returns:
            list[PolicyIntent]: 意图列表
        """
        results = []
        for query in queries:
            try:
                intent = self.understand(query)
                results.append(intent)
            except Exception as e:
                logger.error(f"[IntentAgent] 批量处理失败,query={query}, error={e}")
                results.append(PolicyIntent(
                    policy_id=None,
                    policy_name=None,
                    action_type="资格认定",
                    confidence=0.0,
                    reasoning=f"处理失败: {str(e)}",
                    ambiguities=["系统错误"],
                    need_confirmation=True,
                    candidate_policies=[]
                ))
        return results
