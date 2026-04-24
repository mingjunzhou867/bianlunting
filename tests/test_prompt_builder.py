from cognition.evidence_planner import EvidencePlanItem
from text2sql.dynamic.prompt_builder import QueryPromptBuilder


def _make_plan_item(rule_id: str, rule_name: str) -> EvidencePlanItem:
    return EvidencePlanItem(
        plan_item_id=f"plan_{rule_id.lower()}",
        rule_id=rule_id,
        rule_name=rule_name,
        rule_description="测试规则描述",
        rule_type="灵活评判",
        sql_template=(
            "SELECT pay_month, pay_base FROM social_insurance_payment "
            "WHERE id_card = 'id_card_replace'"
        ),
        priority=120,
        scenario_category="主动服务",
    )


def test_prompt_builder_adds_window_function_guardrails_for_flex_rule() -> None:
    builder = QueryPromptBuilder()
    plan_item = _make_plan_item("P001_FLEX_004", "缴费基数异常波动风险提示")

    prompt = builder.build_system_prompt(plan_item, "42090219800101000A")

    assert "必须先在子查询或 CTE 中计算" in prompt
    assert "严禁在同一层 SELECT 中直接在 WHERE 或 HAVING 引用窗口函数别名" in prompt
    assert "不是证明“必须存在波动”" in prompt


def test_prompt_builder_retry_hint_mentions_subquery_for_window_function_errors() -> None:
    builder = QueryPromptBuilder()
    plan_item = _make_plan_item("P001_FLEX_004", "缴费基数异常波动风险提示")

    retry_prompt = builder.build_user_prompt(
        plan_item,
        "42090219800101000A",
        error_msg=(
            "You cannot use the alias 'prev_pay_base' of an expression containing a window "
            "function in this context."
        ),
    )

    assert "子查询或 CTE" in retry_prompt
    assert "窗口函数别名" in retry_prompt


def test_prompt_builder_keeps_generic_prompt_for_other_rules() -> None:
    builder = QueryPromptBuilder()
    plan_item = _make_plan_item("P001_FLEX_003", "是否存在身份切换风险")

    prompt = builder.build_system_prompt(plan_item, "42090219800101000A")

    assert "不是证明“必须存在波动”" not in prompt
