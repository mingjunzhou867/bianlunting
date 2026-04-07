"""Text-to-SQL tool for agent tool calling."""
import json
from sqlalchemy import text
from config.database import get_session
from text2sql.dynamic.text2sql_agent import Text2SQLAgent
from cognition.evidence_planner import EvidencePlanItem, QuestionType


class Text2SQLTool:
    """Text-to-SQL 工具"""

    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "text_to_sql",
                "description": "根据自然语言查询意图生成并执行SQL，返回查询结果。用于查询人员的具体信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "查询意图，例如：查询该人员的退休年龄、查询该人员的就业状态"
                        },
                        "person_id": {
                            "type": "string",
                            "description": "身份证号"
                        },
                        "table_hints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "相关表名提示，可选"
                        },
                        "dict_refs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "相关字段名提示，可选"
                        }
                    },
                    "required": ["intent", "person_id"]
                }
            }
        }

    def execute(self, intent: str, person_id: str, table_hints=None, dict_refs=None) -> str:
        plan_item = EvidencePlanItem(
            plan_item_id=intent[:10],
            rule_id=intent[:10],
            rule_name=intent,
            rule_description=intent,
            rule_type="灵活评判",
            sql_template="",
            priority=100,
        )

        agent = Text2SQLAgent()
        sql = agent.generate_sql(plan_item, person_id)
        executable_sql = sql.replace("id_card_replace", person_id)

        try:
            with get_session() as session:
                result = session.execute(text(executable_sql))
                rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]

            return json.dumps({
                "status": "success",
                "sql": executable_sql,
                "data": rows,
                "row_count": len(rows)
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "sql": executable_sql,
                "error": str(e)
            }, ensure_ascii=False)
