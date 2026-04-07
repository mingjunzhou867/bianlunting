import re
from loguru import logger
from typing import Optional

from config.llm_client import llm_chat
from text2sql.dynamic.prompt_builder import QueryPromptBuilder
from cognition.evidence_planner import EvidencePlanItem


class Text2SQLAgent:
    """
    动态 SQL 生成智能体。
    依据 Layer 1 产生的规划，通过 LLM 生成精确的 SQL，自带提取能力。
    """
    
    def __init__(self, prompt_builder: QueryPromptBuilder | None = None, model: str = ""):
        self.prompt_builder = prompt_builder or QueryPromptBuilder()
        self.model = model  # 如果为空，llm_chat 内部会走 settings.default_llm_model

    def generate_sql(self, plan_item: EvidencePlanItem, person_id: str, error_feedback: str = "") -> str:
        """
        调用 LLM 生成 SQL。
        如果是报错后的重试调用，会把错误信息通过 error_feedback 传给模型。
        """
        system_prompt = self.prompt_builder.build_system_prompt(plan_item, person_id)
        user_prompt = self.prompt_builder.build_user_prompt(plan_item, person_id, error_msg=error_feedback)

        logger.debug(f"[Text2SQL Agent] 准备生成 SQL，目标：{plan_item.rule_id} ({plan_item.rule_name})")
        
        response = llm_chat(
            system_prompt=system_prompt,
            user_message=user_prompt,
            temperature=0.1  # SQL 生成需要极高的确定性
        )
        
        return self._extract_sql(response)

    def _extract_sql(self, text: str) -> str:
        """
        从大模型返回的文本中提取被 markdown 包裹的 sql 代码。
        """
        match = re.search(r"```[sS][qQ][lL]\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        # 如果模型没有遵守 markdown 格式，尝试退化处理
        logger.warning("模型未输出 markdown sql 块，尝试直接清理并返回原文")
        return text.strip("` \n")
