"""
policy_rule_loader.py - 从数据库加载政策规则

从 rule_definitions 表读取规则，按 rule_type 分类：
- 必须满足：硬性通过条件，程序直接执行
- 必须排除：硬性拒绝条件，程序直接执行
- 灵活评判：需要 Agent 推理和工具调用的规则
"""
from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import text

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

    def _normalize_rule(self, policy_id: str, rule: PolicyRule) -> PolicyRule:
        """Apply runtime guardrails for rules that need tighter semantics."""
        if policy_id == "POLICY_001" and rule.rule_id == "P001_MUST_003":
            return PolicyRule(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                rule_description=rule.rule_description,
                rule_type=rule.rule_type,
                sql_template=(
                    "SELECT "
                    "id_card, hardship_category, hardship_category_code, hardship_policy_match, "
                    "apply_date, certify_org, is_valid "
                    "FROM hardship_certification "
                    "WHERE id_card = :id_card "
                    "  AND is_valid = '1' "
                    "ORDER BY apply_date DESC "
                    "LIMIT 1"
                ),
                scenario_category=rule.scenario_category,
                priority=rule.priority,
            )
        if policy_id == "POLICY_001" and rule.rule_id == "P001_FLEX_004":
            return PolicyRule(
                rule_id=rule.rule_id,
                rule_name="缴费基数异常波动风险提示",
                rule_description=(
                    "分析灵活就业期间缴费基数是否存在大幅异常波动。"
                    "仅当出现明显异常升降时，提示经营异常或数据异常风险；"
                    "连续稳定或轻微波动不得作为不符合资格的依据，可列入需要关注事项。"
                ),
                rule_type=rule.rule_type,
                sql_template=rule.sql_template,
                scenario_category=rule.scenario_category,
                priority=rule.priority,
            )
        return rule

    def load_rules(self, policy_id: str) -> PolicyRuleSet:
        """
        加载指定政策的所有规则，按 rule_type 分类

        Args:
            policy_id: 政策ID，如 'POLICY_001'

        Returns:
            PolicyRuleSet: 分类后的规则集合
        """
        with get_session() as session:
            query = text(
                """
                SELECT
                    rule_id, rule_name, rule_description, rule_type,
                    sql_template, scenario_category, priority
                FROM rule_definitions
                WHERE policy_id = :policy_id
                  AND is_enabled = '1'
                ORDER BY priority ASC, rule_id ASC
                """
            )
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
            rule = self._normalize_rule(policy_id, rule)

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
