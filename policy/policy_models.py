"""
政策相关数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date


class PolicyRule(BaseModel):
    """单条政策规则"""
    rule_id: str = Field(..., description="规则ID")
    description: str = Field(..., description="规则描述")
    check_fields: Optional[List[str]] = Field(None, description="检查字段")
    pass_condition: Optional[str] = Field(None, description="通过条件")
    fail_condition: Optional[str] = Field(None, description="失败条件")
    check_logic: Optional[str] = Field(None, description="检查逻辑")
    formula: Optional[str] = Field(None, description="计算公式")
    sql_template_ref: Optional[str] = Field(None, description="SQL模板引用")


class StructuredRules(BaseModel):
    """结构化规则集"""
    basic_conditions: List[PolicyRule] = Field(default_factory=list, description="基础条件")
    exclusion_conditions: List[PolicyRule] = Field(default_factory=list, description="排斥条件")
    inference_rules: List[PolicyRule] = Field(default_factory=list, description="合理推断规则")
    calculation_rules: List[PolicyRule] = Field(default_factory=list, description="计算规则")


class PolicyConfig(BaseModel):
    """政策完整配置"""
    policy_id: str = Field(..., description="政策ID")
    policy_name: str = Field(..., description="政策名称")
    policy_type: str = Field(..., description="政策类型")
    effective_date: Optional[str] = Field(None, description="生效日期")
    expiry_date: Optional[str] = Field(None, description="失效日期")
    description: str = Field(..., description="政策描述")
    
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    intent_patterns: List[str] = Field(default_factory=list, description="意图匹配模式")
    
    policy_source_files: List[str] = Field(default_factory=list, description="政策原文件路径")
    policy_text: str = Field("", description="政策原文")
    
    structured_rules: StructuredRules = Field(default_factory=StructuredRules, description="结构化规则")
    
    evidence_plan_template: Dict[str, List[str]] = Field(default_factory=dict, description="取证计划模板")
    
    notes: List[str] = Field(default_factory=list, description="备注")
