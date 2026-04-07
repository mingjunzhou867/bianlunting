"""Tool registry for agent tool calling."""
import json
from typing import Any


class ToolRegistry:
    """统一的工具注册中心"""

    def __init__(self):
        self.tools = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        from tools.text2sql_tool import Text2SQLTool
        from tools.dict_tool import DictTool

        self.register("text_to_sql", Text2SQLTool())
        self.register("get_dict", DictTool())

    def register(self, name: str, tool: Any):
        self.tools[name] = tool

    def get_tool_schemas(self) -> list[dict]:
        """返回 OpenAI Tool Calling 格式的工具描述"""
        return [tool.to_schema() for tool in self.tools.values()]

    def execute(self, tool_name: str, arguments: dict) -> str:
        """执行工具调用"""
        tool = self.tools.get(tool_name)
        if not tool:
            return json.dumps({"status": "error", "error": f"工具 {tool_name} 不存在"}, ensure_ascii=False)
        return tool.execute(**arguments)
