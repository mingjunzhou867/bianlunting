import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from pydantic import BaseModel

from cognition.evidence_planner import EvidencePlanItem
from config.llm_client import llm_chat


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
    证据转译装配器。
    将数据库的 Raw JSON 结果转成下游 Agent 易于理解的自然语言摘要。
    """

    def _question_text(self, plan_item: EvidencePlanItem) -> str:
        return getattr(plan_item, "question_text", None) or plan_item.rule_name

    def _expected_answer_shape(self, plan_item: EvidencePlanItem) -> str:
        return getattr(plan_item, "expected_answer_shape", None) or plan_item.rule_description

    def _rule_specific_guidance(self, plan_item: EvidencePlanItem) -> str:
        if plan_item.rule_id == "P001_FLEX_004":
            return (
                "补充约束：这是“异常波动风险提示”而不是资格否决条款。"
                "只有证据明确显示缴费基数出现大幅异常波动时，才可概括为需要关注的风险信号；"
                "若缴费基数连续稳定、无明显波动或仅轻微变化，必须表述为“未发现异常波动”，"
                "supports_conclusion 必须为 null，不得解释为负面证据，更不得据此推导“不符合资格”。"
            )
        return "若原始数据仅能反映普通稳定状态，请保持中性概括，避免把“未见异常”误写成反向风险。"

    def assemble(self, plan_item: EvidencePlanItem, raw_data: list[dict[str, Any]]) -> AssemblerResult:
        if not raw_data:
            return AssemblerResult(
                result_summary="数据库未返回任何记录。未能查证到当前事实。",
                supports_conclusion=None,
            )

        data_str = json.dumps(raw_data, ensure_ascii=False, default=_json_serialize_db_value)

        system_prompt = f"""你是一个高级政务核查结果转译专员。你需要根据底层数据库吐出的 JSON 结果集，结合设定的核心核查提问，输出一段对其他 AI 裁判高度友好的自然语言判断论据。
【我们要核查的具体问题】{self._question_text(plan_item)}

【我们的期望】{self._expected_answer_shape(plan_item)}

【规则特定约束】{self._rule_specific_guidance(plan_item)}

【你的任务】
1. 用一句流畅连贯的中文，清晰概括出这条 JSON 意味着什么，避免直接复述 JSON 语法。
2. 根据这个数据本身，明确回答它是“支持了条件”“违背了条件”还是“没有足够依据表明”。

【输出格式】严格输出纯净无瑕的 JSON 对象：
{{
  "result_summary": "提取出来的关键证据陈述文本",
  "supports_conclusion": true / false / null
}}
"""
        user_prompt = (
            f"【查出的原始数据如下】\n{data_str}\n\n"
            "请不要多言，直接给出转译后的 JSON。"
        )

        try:
            response = llm_chat(system_prompt, user_prompt, temperature=0.1)
            clean_res = response.strip("` \n").removeprefix("json").strip()
            parsed = json.loads(clean_res)

            return AssemblerResult(
                result_summary=parsed.get("result_summary", str(data_str)),
                supports_conclusion=parsed.get("supports_conclusion"),
            )
        except Exception as e:
            logger.warning(f"[EvidenceAssembler] LLM 转译 JSON 失败，启用兜底摘要: {e}")
            return AssemblerResult(
                result_summary=f"提取到 {len(raw_data)} 条记录片段：{str(raw_data[:2])}...",
                supports_conclusion=None,
            )
