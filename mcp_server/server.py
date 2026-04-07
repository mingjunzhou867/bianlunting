import json
from pathlib import Path
from typing import Any, List

from mcp.server.fastmcp import FastMCP
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from config.database import get_session
from cognition.evidence_planner import EvidencePlanItem, QuestionType
from text2sql.dynamic.text2sql_agent import Text2SQLAgent

# 初始化我们的 FastMCP 服务节点
mcp = FastMCP("BysjT2S_MCP_Server")
DICTS_DIR = Path(__file__).parent.parent / "scripts" / "dicts"

@mcp.tool()
def get_dict(field_name: str) -> str:
    """
    按字段对应的专属字典别名加载并返回字典的 JSON 字符串内容。
    用于让 Agent 理解诸如 hardship_category 等字段的码值对应关系，解决“不知道 101 代表什么”的幻觉。
    """
    if not DICTS_DIR.exists():
        return f"字典目录 {DICTS_DIR} 不存在，可能还未通过 generate_dicts.py 初始化。"
        
    for file in DICTS_DIR.glob("*.json"):
        try:
            content = file.read_text(encoding="utf-8")
            data = json.loads(content)
            # 匹配文件名或里面的 field_name
            if field_name.lower() in file.stem.lower() or field_name.lower() in data.get("name", "").lower():
                # 提取摘要 (excerpt-first 原则)
                excerpt = {
                    "dict_id": file.stem,
                    "description": data.get("description", ""),
                    "values": data.get("values", {})
                }
                return json.dumps(excerpt, ensure_ascii=False)
        except Exception:
            continue
            
    return f"未找到名为 '{field_name}' 的字典实体或相关映射。请勿自己猜想枚举值含义。"


@mcp.tool()
def text_to_sql(intent: str, table_hints: List[str], dict_refs: List[str], person_id: str) -> str:
    """
    通用代理 SQL 生成器入口：接收自然语言查询意图和表提示，
    动态生成 SQL 并执行一次，直接返回结果集。
    注意：在 Prompt 中会强制将身份证标识转换为占位符执行。
    """
    # 借助系统原本强大的 PromptBuilder 链路构建 PlanItem
    dummy_plan = EvidencePlanItem(
        plan_item_id=intent[:10],
        rule_id=intent[:10],
        rule_name=intent,
        rule_description=intent,
        rule_type="灵活评判",
        sql_template="",
        priority=100,
    )
    
    agent = Text2SQLAgent()
    sql = agent.generate_sql(dummy_plan, person_id)
    executable_sql = sql.replace("id_card_replace", person_id)
    
    try:
        with get_session() as session:
            result = session.execute(text(executable_sql))
            rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        
        return json.dumps({
            "generated_sql": executable_sql,
            "status": "success",
            "data": rows
        }, ensure_ascii=False)
    except SQLAlchemyError as exc:
        return json.dumps({
            "generated_sql": executable_sql,
            "status": "error",
            "error_msg": str(exc),
            "suggestion": "请调用 auto_debug_sql 工具，并将当前错误信息传入进行修复"
        }, ensure_ascii=False)


@mcp.tool()
def auto_debug_sql(sql_with_bug: str, error_msg: str, intent: str, table_hints: List[str], dict_refs: List[str], person_id: str) -> str:
    """
    接收之前执行失败的 SQL 以及它的错误信息，借助大模型的反思能力，
    重新生成修正后的 SQL 并再次尝试执行。
    """
    dummy_plan = EvidencePlanItem(
        plan_item_id=intent[:10],
        rule_id=intent[:10],
        rule_name=intent,
        rule_description=intent,
        rule_type="灵活评判",
        sql_template="",
        priority=100,
    )
    
    agent = Text2SQLAgent()
    sql = agent.generate_sql(dummy_plan, person_id, error_feedback=error_msg)
    executable_sql = sql.replace("id_card_replace", person_id)
    
    try:
        with get_session() as session:
            result = session.execute(text(executable_sql))
            rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        
        return json.dumps({
            "repaired_sql": executable_sql,
            "status": "success",
            "data": rows
        }, ensure_ascii=False)
    except SQLAlchemyError as exc:
        return json.dumps({
            "repaired_sql": executable_sql,
            "status": "error",
            "error_msg": str(exc)
        }, ensure_ascii=False)


if __name__ == "__main__":
    # 使用 FastMCP 提供的 stdio 标准传输流启动
    mcp.run(transport="stdio")
