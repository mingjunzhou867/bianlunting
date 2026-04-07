import json
import re
from pathlib import Path
from typing import Any

from cognition.evidence_planner import EvidencePlanItem


class DDLManager:
    """Manages reading and extracting specific table definitions from the DDL file."""
    
    def __init__(self, ddl_path: str | Path | None = None):
        if ddl_path is None:
            # 默认指向项目中的 mysql_ddl.sql
            self.ddl_path = Path(__file__).resolve().parent.parent.parent / "data" / "schema" / "mysql_ddl.sql"
        else:
            self.ddl_path = Path(ddl_path)
            
        self._table_cache: dict[str, str] = {}
        self._load_and_parse_ddl()
        
    def _load_and_parse_ddl(self):
        if not self.ddl_path.exists():
            return
            
        content = self.ddl_path.read_text(encoding="utf-8")
        
        # 简单的正则匹配 CREATE TABLE 语句块
        # 匹配 CREATE TABLE [IF NOT EXISTS] table_name ( ... ) ENGINE=...;
        pattern = re.compile(
            r"CREATE TABLE IF NOT EXISTS ([a-zA-Z0-9_]+) \((.*?)\) ENGINE=.*?COMMENT='.*?';",
            re.IGNORECASE | re.DOTALL
        )
        for match in pattern.finditer(content):
            table_name = match.group(1).lower()
            # 保存完整的建表语句作为提示词上下文
            self._table_cache[table_name] = match.group(0)

    def get_table_ddl(self, table_name: str) -> str:
        return self._table_cache.get(table_name.lower(), f"-- 找不到表 {table_name} 的定义")


class DictManager:
    """Manages loading dictionary JSON excerpts based on field names."""
    def __init__(self, dicts_dir: str | Path | None = None):
        if dicts_dir is None:
            self.dicts_dir = Path(__file__).resolve().parent.parent.parent / "scripts" / "dicts"
        else:
            self.dicts_dir = Path(dicts_dir)
            
    def get_dict_excerpt(self, field_name: str) -> str:
        if not self.dicts_dir.exists():
            return ""
            
        for file in self.dicts_dir.glob("*.json"):
            try:
                content = file.read_text(encoding="utf-8")
                data = json.loads(content)
                name = data.get("name", "").lower()
                aliases = [a.lower() for a in data.get("aliases", [])]
                
                f_lower = field_name.lower()
                if f_lower in file.stem.lower() or f_lower in name or f_lower in aliases:
                    excerpt = {
                        "field": field_name,
                        "dict_name": data.get("name"),
                        "description": data.get("description", ""),
                        "values": data.get("values", {})
                    }
                    return json.dumps(excerpt, ensure_ascii=False)
            except Exception:
                continue
        return ""


class QueryPromptBuilder:
    """
    负责将 Layer 1 的 EvidencePlanItem 转换为大模型可以直接阅读的高质量 Text-to-SQL Prompt。
    核心逻辑是“动态裁剪”：只给大模型看它必须看的表结构和字典要求。
    """
    def __init__(self, ddl_manager: DDLManager | None = None, dict_manager: DictManager | None = None):
        self.ddl_manager = ddl_manager or DDLManager()
        self.dict_manager = dict_manager or DictManager()

    def build_system_prompt(self, plan_item: EvidencePlanItem, person_id: str) -> str:
        """组装系统级 Prompt"""

        # 1. 从 sql_template 中提取表名（简单解析）
        import re
        sql_template = plan_item.sql_template or ""
        table_pattern = r'FROM\s+`?(\w+)`?|JOIN\s+`?(\w+)`?'
        matches = re.findall(table_pattern, sql_template, re.IGNORECASE)
        target_tables = [t for match in matches for t in match if t]

        ddl_contexts = []
        for table in target_tables:
            ddl_contexts.append(self.ddl_manager.get_table_ddl(table))
        ddl_str = "\n\n".join(ddl_contexts) if ddl_contexts else "（无特定表结构约束）"

        # 2. 字典摘录（暂时跳过，因为没有 relevant_fields）
        dict_str = "（本次查询无特定枚举字典约束，请直接选用原始值）"

        # 3. 关联关系提示
        relations_str = "如果目标涉及多张表，通常使用 `id_card` 或 `company_name` 字段进行 JOIN。优先过滤 `is_valid` = '1' 或 `data_status` = '1' 的有效记录。"

        # 4. 重点字段（暂时跳过）
        fields_str = "（根据规则描述自行判断）"

        # 5. 约束与指引（暂时跳过）
        notes_str = "（无额外约束）"

        system_prompt = f"""你是一个顶级的数据库专家（DBA）与政务数据分析师。
你的任务是根据传入的业务核查需求，编写一条【准确且能在 MySQL 8.0 中直接执行】的 SQL 查询语句。

【任务背景与要求】
你需要查清楚的问题是：{plan_item.rule_name}
规则描述：{plan_item.rule_description}

【非常重要的安全占位符要求】
为支持后续系统的批量映射，当你在撰写涉及人员核查的 SQL 查询（通常是针对表中的 id_card 字段）时，请务必使用固定的占位符字符串 'id_card_replace'（必须包含单引号）。
错误示例：id_card = '{person_id}'
正确示例：id_card = 'id_card_replace'

【SQL 模板参考】
{sql_template if sql_template else '（无模板，请根据规则描述自行编写）'}

【相关的数据库表结构 (DDL)】
以下是你能够使用的表结构定义（只展示了本次任务相关的表）：
```sql
{ddl_str}
```

【关联关系指引 (Relations)】
{relations_str}

【字典枚举映射 (DictExcerpt)】
为了防止幻觉，请【务必遵守】以下业务字典定义的码值转换逻辑，绝不可自己编造字典中不存在的枚举值含义：
{dict_str}

【你必须重点关注和提取的字段】
{fields_str}

【输出要求】
1. 只输出能够在 MySQL 中执行的纯正 SELECT 查询语句，不要有任何多余的解释文字。
2. 必须且只能返回查询得到的数据，如果有枚举值判断，请严格遵守 DDL 中 COMMENT 及提示词中的字典定义。
3. 如果需要查询最新的一条记录，请记得使用 ORDER BY ... DESC LIMIT 1。
4. 所有的 WHERE 条件中涉及身份标识过滤时，严格使用 id_card = 'id_card_replace' 作为安全占位符。
5. 输出格式请严格遵守 Markdown 的 ```sql ... ``` 格式。
"""
        return system_prompt

    def build_user_prompt(self, plan_item: EvidencePlanItem, person_id: str, error_msg: str = "") -> str:
        """
        组装用户级 Prompt。如果是第一次生成，只需触发；
        如果是 AutoDebugger 重试，则会携带 error_msg。
        """
        if error_msg:
            return f"""你之前生成的 SQL 语句在执行时遇到了如下错误，请修正并重新输出一条正确的 SQL：
错误信息：
{error_msg}

请直接输出修正后的 SQL 语句。"""
        
        return "请根据上述结构和需求，生成 SQL 语句。"
