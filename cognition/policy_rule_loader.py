"""
policy_rule_loader.py — 从数据库加载政策规则

从 rule_definitions 表读取规则，按 rule_type 分类：
- 必须满足：硬性通过条件，程序直接执行
- 必须排除：硬性拒绝条件，程序直接执行
- 灵活评判：需要 Agent 推理和工具调用的规则
"""
from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import text
from loguru import logger

from config.database import get_session


@dataclass
class PolicyRule:
    rule_id: str
    rule_name: str
    rule_description: str
    rule_type: str  # 必须满足/必须排除/灵活评判
    sql_template: str
    scenario_category: str | None
    priority: int


@dataclass
class PolicyRuleSet:
    policy_id: str
    must_satisfy: list[PolicyRule]  # 必须满足
    must_exclude: list[PolicyRule]  # 必须排除
    flexible: list[PolicyRule]      # 灵活评判


class PolicyRuleLoader:
    """从数据库加载政策规则"""

    def load_rules(self, policy_id: str) -> PolicyRuleSet:
        """
        加载指定政策的所有规则，按 rule_type 分类

        Args:
            policy_id: 政策ID，如 'POLICY_001'

        Returns:
            PolicyRuleSet: 分类后的规则集合
        """
        with get_session() as session:
            query = text("""
                SELECT
                    rule_id, rule_name, rule_description, rule_type,
                    sql_template, scenario_category, priority
                FROM rule_definitions
                WHERE policy_id = :policy_id
                  AND is_enabled = '1'
                ORDER BY priority ASC, rule_id ASC
            """)
            rows = session.execute(query, {"policy_id": policy_id}).fetchall()

        must_satisfy = []
        must_exclude = []
        flexible = []

        for row in rows:
            rule = PolicyRule(
                rule_id=row.rule_id,
                rule_name=row.rule_name,
                rule_description=row.rule_description or "",
                rule_type=row.rule_type,
                sql_template=row.sql_template,
                scenario_category=row.scenario_category,
                priority=row.priority,
            )

            if rule.rule_type == "必须满足":
                must_satisfy.append(rule)
            elif rule.rule_type == "必须排除":
                must_exclude.append(rule)
            elif rule.rule_type == "灵活评判":
                flexible.append(rule)

        logger.info(
            f"加载政策规则 {policy_id}: "
            f"必须满足={len(must_satisfy)}, 必须排除={len(must_exclude)}, 灵活评判={len(flexible)}"
        )

        return PolicyRuleSet(
            policy_id=policy_id,
            must_satisfy=must_satisfy,
            must_exclude=must_exclude,
            flexible=flexible,
        )
