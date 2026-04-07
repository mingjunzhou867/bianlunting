"""Dictionary lookup tool for agent tool calling."""
import json
from pathlib import Path


class DictTool:
    """数据字典查询工具"""

    def __init__(self):
        self.dicts_dir = Path(__file__).parent.parent / "scripts" / "dicts"

    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_dict",
                "description": "查询数据字典，了解字段的枚举值含义。例如：hardship_category 的 101 代表什么。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field_name": {
                            "type": "string",
                            "description": "字段名称，例如：hardship_category、employment_form"
                        }
                    },
                    "required": ["field_name"]
                }
            }
        }

    def execute(self, field_name: str) -> str:
        if not self.dicts_dir.exists():
            return json.dumps({
                "status": "error",
                "error": f"字典目录不存在"
            }, ensure_ascii=False)

        for file in self.dicts_dir.glob("*.json"):
            try:
                content = file.read_text(encoding="utf-8")
                data = json.loads(content)
                if field_name.lower() in file.stem.lower() or field_name.lower() in data.get("name", "").lower():
                    return json.dumps({
                        "status": "success",
                        "dict_id": file.stem,
                        "description": data.get("description", ""),
                        "values": data.get("values", {})
                    }, ensure_ascii=False)
            except Exception:
                continue

        return json.dumps({
            "status": "error",
            "error": f"未找到字段 '{field_name}' 的字典"
        }, ensure_ascii=False)
