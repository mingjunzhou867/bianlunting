from cognition.policy_rule_loader import PolicyRule, PolicyRuleLoader


def test_normalize_flex_base_rule_to_risk_hint() -> None:
    loader = PolicyRuleLoader()
    raw_rule = PolicyRule(
        rule_id="P001_FLEX_004",
        rule_name="缴费基数波动分析",
        rule_description="分析灵活就业期间缴费基数是否存在异常波动，大幅下降可能表示经营困难或数据异常",
        rule_type="灵活评判",
        sql_template="SELECT pay_month, pay_base FROM social_insurance_payment",
        scenario_category="主动服务",
        priority=120,
    )

    normalized = loader._normalize_rule("POLICY_001", raw_rule)

    assert normalized.rule_name == "缴费基数异常波动风险提示"
    assert "大幅异常波动" in normalized.rule_description
    assert "连续稳定或轻微波动不得作为不符合资格的依据" in normalized.rule_description


def test_other_rules_are_not_changed() -> None:
    loader = PolicyRuleLoader()
    raw_rule = PolicyRule(
        rule_id="P001_FLEX_003",
        rule_name="是否存在身份切换风险",
        rule_description="检查insurance_change_log中是否有即将发生的身份切换",
        rule_type="灵活评判",
        sql_template="SELECT * FROM insurance_change_log",
        scenario_category="主动服务",
        priority=110,
    )

    normalized = loader._normalize_rule("POLICY_001", raw_rule)

    assert normalized == raw_rule
