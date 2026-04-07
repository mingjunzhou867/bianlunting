"""
意图理解相关数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class CandidatePolicy(BaseModel):
    """候选政策"""
    policy_id: str = Field(..., description="政策ID")
    policy_name: str = Field(..., description="政策名称")
    match_reason: str = Field(..., description="匹配原因")
    match_score: float = Field(..., ge=0.0, le=1.0, description="匹配得分 0.0~1.0")


class PolicyIntent(BaseModel):
    """政策意图识别结果"""
    policy_id: Optional[str] = Field(None, description="政策ID")
    policy_name: Optional[str] = Field(None, description="政策名称")
    action_type: str = Field(..., description="行动类型: 资格认定/金额计算/历史查询/疑似人员识别")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0.0~1.0")
    reasoning: str = Field(..., description="推理过程")
    ambiguities: List[str] = Field(default_factory=list, description="歧义点")
    need_confirmation: bool = Field(..., description="是否需要二次确认")
    candidate_policies: List[CandidatePolicy] = Field(default_factory=list, description="候选政策列表")
