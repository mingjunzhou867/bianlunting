import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from loguru import logger
from pydantic import BaseModel

from config.llm_client import llm_chat
from cognition.evidence_planner import EvidencePlanItem


class AssemblerResult(BaseModel):
    result_summary: str
    supports_conclusion: bool | None


def _json_serialize_db_value(obj: Any) -> Any:
    """SQLAlchemy/MySQL 常返回 Decimal、date/datetime，标准 json 无法直接序列化。"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class EvidenceAssembler:
    """
    证据转译装配车间。
    将数据库无温度的 Raw JSON 翻译成下游裁判 Agent 能“一眼看懂”的高质量自然语言摘要。
    """
    
    def _question_text(self, plan_item: EvidencePlanItem) -> str:
        return getattr(plan_item, "question_text", None) or plan_item.rule_name

    def _expected_answer_shape(self, plan_item: EvidencePlanItem) -> str:
        return getattr(plan_item, "expected_answer_shape", None) or plan_item.rule_description

    def assemble(self, plan_item: EvidencePlanItem, raw_data: list[dict[str, Any]]) -> AssemblerResult:
        if not raw_data:
            return AssemblerResult(
                result_summary="数据库未返回任何记录。未能查证到当前事实。",
                supports_conclusion=None
            )

        data_str = json.dumps(
            raw_data, ensure_ascii=False, default=_json_serialize_db_value
        )
        
        system_prompt = f"""你是一个高级政务核查结果转译专员。
你需要根据底层数据库吐出的 JSON 结果集，结合设定的核心核查提问，输出一段对其它AI裁判员高度友好的自然语言判断论据。

【我们要核查的具体问题】
{self._question_text(plan_item)}

【我们的期望】
{self._expected_answer_shape(plan_item)}

【你的任务】
1. 用一句流利连贯的中文，清晰概括出这条 JSON 意味着什么（切忌暴露 JSON 语法大括号，只提取如：金额、状态码含义等，必须说人话）。
2. 根据这个数据本身，明确回答它是否“支持了条件”、“违背了条件”，或者“没有足够依据表明”。

【输出格式】
严格输出纯净无瑕的 JSON 对象：
{{
  "result_summary": "提取出来的关键证据陈述文本（例如：已查实该人员存在企业法人的未注销工商记录...）",
  "supports_conclusion": true / false / null (若属于中性推断请给 null)
}}
"""
        user_prompt = f"【查出的原始僵硬数据如下】\n{data_str}\n\n请不要多言，直接给出转译后的 JSON："

        # 低温提取，保证 JSON 的完全纯粹
        try:
            response = llm_chat(system_prompt, user_prompt, temperature=0.1)
            # 暴力撕掉大模型自作多情带上的 Markdown 标记
            clean_res = response.strip("` \n").removeprefix("json").strip()
            parsed = json.loads(clean_res)
            
            return AssemblerResult(
                result_summary=parsed.get("result_summary", str(data_str)),
                supports_conclusion=parsed.get("supports_conclusion")
            )
        except Exception as e:
            logger.warning(f"[EvidenceAssembler] LLM 转译 Json 崩解，启用暴力拼接防线: {e}")
            return AssemblerResult(
                result_summary=f"提取到 {len(raw_data)} 条记录片段：{str(raw_data[:2])}...",
                supports_conclusion=None
            )
