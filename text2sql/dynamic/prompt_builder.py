import json
import re
from pathlib import Path
from typing import Any

from cognition.evidence_planner import EvidencePlanItem


class DDLManager:
    """Manages reading and extracting specific table definitions from the DDL file."""

    def __init__(self, ddl_path: str | Path | None = None):
        if ddl_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.ddl_paths = [
                base_dir / "data" / "schema" / "schema_struct.sql",
                base_dir / "schema_struct.sql",
                base_dir / "data" / "schema" / "full_backup.sql",
                base_dir / "data" / "schema" / "mysql_ddl.sql",
            ]
        else:
            self.ddl_paths = [Path(ddl_path)]

        self._table_cache: dict[str, str] = {}
        self._load_and_parse_ddl()

    def _read_ddl_content(self, ddl_path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
            try:
                return ddl_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        # Final fallback to avoid hard failure on unexpected encoding.
        return ddl_path.read_text(encoding="utf-8", errors="ignore")

    def _load_and_parse_ddl(self) -> None:
        pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([a-zA-Z0-9_]+)`?\s*\(.*?\)\s*(?:ENGINE\s*=\s*[^;]+)?;",
            re.IGNORECASE | re.DOTALL,
        )
        for ddl_path in self.ddl_paths:
            if not ddl_path.exists():
                continue
            content = self._read_ddl_content(ddl_path)
            for match in pattern.finditer(content):
                table_name = match.group(1).lower()
                # Keep the first parsed definition so full schema sources win over minimal fallback files.
                self._table_cache.setdefault(table_name, match.group(0))

    def get_table_ddl(self, table_name: str) -> str:
        return self._table_cache.get(table_name.lower(), f"-- 未找到表 {table_name} 的定义")


class DictManager:
    """Manages loading dictionary JSON excerpts based on field names."""

    def __init__(self, dicts_dir: str | Path | None = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        if dicts_dir is None:
            self.dict_dirs = [
                base_dir / "dicts",
                base_dir / "scripts" / "dicts",
            ]
        else:
            self.dict_dirs = [Path(dicts_dir)]

    def get_dict_excerpt(self, field_name: str) -> str:
        for dict_dir in self.dict_dirs:
            if not dict_dir.exists():
                continue

            for file in dict_dir.glob("*.json"):
                try:
                    content = file.read_text(encoding="utf-8")
                    data = json.loads(content)
                    name = data.get("name", "").lower()
                    aliases = [a.lower() for a in data.get("aliases", [])]
                    source_fields = [
                        str(source.get("field", "")).lower()
                        for source in data.get("source_refs", [])
                        if isinstance(source, dict)
                    ]

                    f_lower = field_name.lower()
                    if (
                        f_lower in file.stem.lower()
                        or f_lower in name
                        or f_lower in aliases
                        or f_lower in source_fields
                    ):
                        excerpt = {
                            "field": field_name,
                            "dict_name": data.get("name"),
                            "description": data.get("description", ""),
                            "values": data.get("values", {}),
                        }
                        return json.dumps(excerpt, ensure_ascii=False)
                except Exception:
                    continue
        return ""


class QueryPromptBuilder:
    """
    将 EvidencePlanItem 转成高质量 Text-to-SQL Prompt。
    核心是只给模型当前任务所需的表结构和约束。
    """

    def __init__(self, ddl_manager: DDLManager | None = None, dict_manager: DictManager | None = None):
        self.ddl_manager = ddl_manager or DDLManager()
        self.dict_manager = dict_manager or DictManager()

    def _extract_target_tables(self, sql_template: str) -> list[str]:
        table_pattern = r"FROM\s+`?(\w+)`?|JOIN\s+`?(\w+)`?"
        matches = re.findall(table_pattern, sql_template, re.IGNORECASE)
        return [t for match in matches for t in match if t]

    def _build_allowed_field_clause(self, plan_item: EvidencePlanItem) -> str:
        preferred_fields = plan_item.allowed_fields or plan_item.relevant_fields
        if not preferred_fields:
            return "（未提供字段白名单，必须仅使用 DDL 中真实存在的字段，且不得臆造字段名）"
        return "\n".join(f"- {field}" for field in preferred_fields)

    def _collect_target_tables(self, plan_item: EvidencePlanItem) -> list[str]:
        tables: list[str] = []
        seen: set[str] = set()

        for table in self._extract_target_tables(plan_item.sql_template or ""):
            lower = table.lower()
            if lower not in seen:
                seen.add(lower)
                tables.append(table)

        for field in (plan_item.allowed_fields or []) + (plan_item.relevant_fields or []):
            if "." not in field:
                continue
            table = field.split(".", 1)[0].strip()
            lower = table.lower()
            if table and lower not in seen:
                seen.add(lower)
                tables.append(table)

        for table in plan_item.evidence_targets or []:
            lower = table.lower()
            if table and lower not in seen:
                seen.add(lower)
                tables.append(table)

        return tables

    def _detail_query_rules(self, plan_item: EvidencePlanItem) -> bool:
        detail_rule_ids = {
            "P001_MUST_003",
            "P001_FLEX_002",
            "P001_FLEX_004",
            "P001_FLEX_005",
        }
        keywords = ("调查详情", "详情查询", "明细", "复合表", "联合查询")
        return plan_item.rule_id in detail_rule_ids or any(token in plan_item.rule_name or token in plan_item.rule_description for token in keywords)

    def _rule_specific_notes(self, plan_item: EvidencePlanItem) -> str:
        notes: list[str] = []

        notes.extend(plan_item.notes_for_query_generation or [])
        notes.extend(
            [
                "枚举字段必须使用数据库中存储的编码值，不得把中文含义拼接进字段值。",
                "social_insurance_payment.insurer_status: 单位缴费 -> '101'；个人灵活就业/灵活就业人员缴纳 -> '102'。禁止生成 '101单位缴费' 或 '102个人灵活就业'。",
                "social_insurance_payment.insurance_type: 养老保险 -> '110'；医疗保险/医保 -> '310'。",
                "只有问题明确出现“有效、正常、未作废、当前有效、只算有效”等要求时，才允许追加 is_valid = '1' 或 data_status = '1'；问题要求“所有记录”时禁止默认追加有效状态过滤。",
            ]
        )

        if plan_item.allowed_fields:
            notes.append(
                "Allowed fields (schema-backed only): " + ", ".join(plan_item.allowed_fields)
            )

        if self._detail_query_rules(plan_item):
            notes.extend(
                [
                    "本规则属于详情型核查，不允许仅返回 COUNT(*)、EXISTS 或单一布尔值。",
                    "必须优先返回字段级事实，至少包含状态、类别、时间、来源或政策匹配结果中的可用字段。",
                    "如事实分布在多表中，应使用 JOIN / 子查询 / CTE 组合出可解释的复合查询结果。",
                    "若局部字段缺失，也要返回已获取的明细行，避免把详情型规则退化成空洞的存在性判断。",
                ]
            )

        if plan_item.rule_id == "P001_FLEX_004":
            notes.extend(
                [
                    "本规则目标是识别“缴费基数大幅异常波动”，不是证明“必须存在波动”。",
                    "若使用 LAG、LEAD 等窗口函数，必须先在子查询或 CTE 中计算 prev_pay_base / next_pay_base，"
                    "再在外层 SELECT 的 WHERE 中引用这些列做过滤。",
                    "严禁在同一层 SELECT 中直接在 WHERE 或 HAVING 引用窗口函数别名，例如 prev_pay_base、next_pay_base。",
                    "若数据稳定或仅轻微波动，也应返回可执行 SQL，让结果自然显示“未检出异常”，而不是构造负面条件。",
                ]
            )

        return "\n".join(f"{idx + 1}. {note}" for idx, note in enumerate(notes)) or "（无额外规则特定约束）"

    def build_system_prompt(self, plan_item: EvidencePlanItem, person_id: str) -> str:
        """组装系统 Prompt。"""

        sql_template = plan_item.sql_template or ""
        target_tables = self._collect_target_tables(plan_item)

        ddl_contexts = [self.ddl_manager.get_table_ddl(table) for table in target_tables]
        ddl_str = "\n\n".join(ddl_contexts) if ddl_contexts else "（无特定表结构约束）"

        dict_excerpts = [
            excerpt
            for field_name in ("insurer_status", "insurance_type", "is_valid")
            if (excerpt := self.dict_manager.get_dict_excerpt(field_name))
        ]
        dict_str = "\n".join(dict_excerpts) if dict_excerpts else "（本次查询无外部字典摘录，使用下方内置枚举约束。）"
        enum_constraints_str = """- social_insurance_payment.insurer_status 只能使用编码值：'101'=单位缴费，'102'=个人灵活就业/灵活就业人员缴纳。禁止把中文含义拼进值里，例如禁止 '101单位缴费'、'102个人灵活就业'。
- social_insurance_payment.insurance_type 只能使用编码值：'110'=养老保险，'310'=医疗保险/医保。
- is_valid/data_status 是有效状态字段：只有问题明确要求“有效、正常、未作废、当前有效、只算有效”等语义时才过滤为 '1'；问题说“所有记录”或未提有效状态时，不要默认追加有效状态过滤。"""
        relations_str = (
            "只有当问题或规则明确需要跨表字段时才使用 JOIN；不要仅为了补充姓名、企业名等展示信息而额外 JOIN。"
            "只有当问题或规则明确要求有效记录时，才过滤 `is_valid` = '1' 或 `data_status` = '1'。"
            "当问题要求查询所有记录时，不要默认追加有效状态过滤。"
        )
        fields_str = self._build_allowed_field_clause(plan_item)
        notes_str = self._rule_specific_notes(plan_item)

        allowed_tables = [
            "person",
            "employment_registration",
            "unemployment_registration",
            "hardship_certification",
            "social_insurance_payment",
            "subsidy_payment_history",
            "company_info",
            "company_shareholder",
            "insurance_change_log",
        ]
        allowed_tables_str = "\n".join(f"- {table}" for table in allowed_tables)
        allowed_fields_map = {
            "person": ["id_card", "name", "gender", "birth_date", "hukou_region", "life_status", "system_status", "business_role", "created_at"],
            "employment_registration": ["record_id", "id_card", "company_id", "employment_form", "employment_date", "contract_start_date", "contract_end_date", "sync_date", "is_valid"],
            "unemployment_registration": ["record_id", "id_card", "unemployment_date", "unemployment_reason", "register_date", "cancel_date", "is_valid"],
            "hardship_certification": ["cert_id", "id_card", "hardship_category", "apply_date", "certify_org", "cancel_date", "cancel_reason", "is_valid"],
            "social_insurance_payment": ["payment_id", "id_card", "company_id", "insurance_type", "pay_month", "insurer_status", "pay_base", "is_valid"],
            "subsidy_payment_history": ["payment_id", "id_card", "policy_code", "apply_start_month", "apply_end_month", "first_enjoy_month", "grant_months", "grant_amount", "grant_date", "is_valid"],
            "company_info": ["company_id", "company_name", "legal_person_id_card", "company_type", "is_valid", "created_at"],
            "company_shareholder": ["relation_id", "company_id", "id_card", "share_ratio", "is_valid"],
            "insurance_change_log": ["change_id", "id_card", "insurance_type", "old_status", "new_status", "event_date", "related_company_id", "is_valid"],
        }
        allowed_fields_str = "\n".join(
            f"- {table}: {', '.join(fields)}" for table, fields in allowed_fields_map.items()
        )

        system_prompt = f"""你是一个顶级数据库专家（DBA）与政务数据分析师。你的任务是根据传入的业务核查需求，编写一条能在 MySQL 8.0 直接执行的 SELECT 查询语句。
【任务背景与要求】
你需要核查的问题是：{plan_item.rule_name}
规则描述：{plan_item.rule_description}

【强制表结构约束】
你只能使用下面这些现有表，严禁臆造任何新表名、旧表名或别名拼错的表名：
{allowed_tables_str}

【绝对禁止的旧表名示例】
- unemployment
- social_insurance
- social_insurance_records
- unemployment_records
- subsidy_records
- company_relation

【安全占位符要求】
在撰写涉及人员核查的 SQL 查询时，凡是针对 `id_card` 的过滤，都必须使用固定占位符 `'id_card_replace'`。
错误示例：id_card = '{person_id}'
正确示例：id_card = 'id_card_replace'

【SQL 模板参考】
{sql_template if sql_template else '（无模板，请根据规则描述自行编写）'}

【相关数据库表结构（DDL）】
```sql
{ddl_str}
```

【关联关系提示】
{relations_str}

【字典摘要】
{dict_str}

【枚举与有效状态硬约束】
{enum_constraints_str}

【重点关注字段】
{fields_str}

【允许字段白名单】
{allowed_fields_str}

【查询深度要求】
{'详情型查询：必须返回字段级或复合表事实，不允许仅返回 COUNT(*) / EXISTS。' if self._detail_query_rules(plan_item) else '汇总型查询：可根据规则目标选择最小必要结果集。'}

【字段使用硬约束】
- 生成 SQL 时只能使用上述白名单字段，严禁臆造任何不存在的字段名。
- 禁止使用通用字段名 `id` 代替主键字段。
- 如果需要主键，请显式使用各表真实主键：person.id_card、employment_registration.record_id、unemployment_registration.record_id、hardship_certification.cert_id、social_insurance_payment.payment_id、subsidy_payment_history.payment_id、company_info.company_id、company_shareholder.relation_id、insurance_change_log.change_id。

【规则特定约束】
{notes_str}

【输出要求】
1. 只输出能在 MySQL 中执行的纯 SELECT 查询语句，不要附加解释文字。
2. 必须严格遵守 MySQL 8.0 语法，尤其注意窗口函数别名不能在同层 WHERE/HAVING 直接引用。
3. 如果需要查询最新记录，优先使用 `ORDER BY ... DESC LIMIT 1`。
4. 所有 `id_card` 过滤必须使用 `id_card = 'id_card_replace'`。
5. 任何 `FROM` / `JOIN` 中的表名必须严格来自【强制表结构约束】。
6. 输出格式必须是 Markdown 的 ```sql ... ``` 代码块。"""
        return system_prompt

    def build_user_prompt(self, plan_item: EvidencePlanItem, person_id: str, error_msg: str = "") -> str:
        """
        组装用户 Prompt。
        如果是 AutoDebugger 重试，会附带 error_msg。
        """
        if error_msg:
            extra_hint = (
                "\n修复提示：如果错误表现为结果为空、行数不一致或值不一致，请优先检查枚举编码和值域。"
                "insurer_status 只能使用 '101' 或 '102'，不要生成 '101单位缴费'、'102个人灵活就业'；"
                "insurance_type 只能使用 '110' 或 '310'；"
                "除非问题明确要求有效记录，不要额外追加 is_valid = '1' 或 data_status = '1'。\n"
            )
            lowered = error_msg.lower()
            if "window function" in lowered or "prev_pay_base" in lowered or "next_pay_base" in lowered:
                extra_hint += (
                    "\n修复提示：这类报错通常意味着你在同一层 WHERE/HAVING 里直接使用了窗口函数别名。"
                    "请改成子查询或 CTE：先计算窗口列，再在外层 WHERE 过滤。"
                )

            return (
                f"你之前生成的 SQL 在执行时遇到了如下错误，请修正并重新输出一条正确的 SQL。\n"
                f"错误信息：{error_msg}"
                f"{extra_hint}\n\n"
                "请直接输出修正后的 SQL 语句。"
            )

        return "请根据上述结构和需求，生成 SQL 查询语句。"
