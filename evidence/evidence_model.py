"""Core evidence models shared across retrieval and debate layers."""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Literal

from pydantic import BaseModel, Field


DiagnosticCode = Literal[
    "ok",
    "empty_result",
    "missing_column",
    "missing_table",
    "table_corrupted",
    "sql_error",
    "db_connection_error",
    "query_error",
    "unknown_error",
]


def classify_evidence_diagnostic(
    exec_status: str,
    error_message: str | None = None,
) -> tuple[DiagnosticCode, str, str, str]:
    if exec_status == "success":
        return ("ok", "查询成功", "查询成功并返回了结果。", "结果可直接用于后续判断。")
    if exec_status == "no_data":
        return ("empty_result", "正确表中无结果", "SQL 执行成功，但没有匹配记录。", "优先核对业务上是否允许“查无记录”被解释为未触发风险。")
    if exec_status == "field_missing":
        return ("missing_column", "字段缺失", "查询依赖的字段不存在或列名不匹配。", "检查字段名、视图字段映射和数据字典。")

    msg = (error_message or "").lower()
    if re.search(r"unknown column|no such column|invalid column|column .* does not exist", msg):
        return ("missing_column", "字段缺失", "SQL 引用了不存在的字段。", "检查字段名是否变更，或是否查错了视图/表。")
    if re.search(r"doesn't exist|does not exist|no such table|unknown table", msg):
        return ("missing_table", "表不存在或查错表", "SQL 引用了不存在的表，或当前库缺少目标表。", "检查库连接、表名和 SQL 模板是否指向正确数据源。")
    if re.search(r"marked as crashed|is crashed|corrupt|incorrect key file", msg):
        return ("table_corrupted", "表损坏", "底层表或索引损坏，查询无法正常执行。", "优先检查数据库表健康状态并修复索引/表。")
    if re.search(r"syntax|parse|1064|near ", msg):
        return ("sql_error", "SQL 语法错误", "生成或拼装出来的 SQL 不合法。", "检查 SQL 模板或生成逻辑。")
    if re.search(r"connection|connect|gone away|timeout|refused|server has gone away|can't connect", msg):
        return ("db_connection_error", "数据库连接异常", "查询未到业务表层，已在数据库连接或会话层失败。", "检查数据库服务、网络连通性和连接配置。")
    if error_message:
        return ("query_error", "查询执行异常", f"查询执行失败：{error_message}", "需要结合报错信息排查 SQL、权限或底层库状态。")
    return ("unknown_error", "未知异常", "查询失败，但没有可识别的具体原因。", "需要补充日志或保留原始报错进一步排查。")


class EvidenceItem(BaseModel):
    """One normalized evidence record produced by the retrieval layer."""

    evidence_id: str = Field(description="Stable evidence identifier")
    rule_id: str = Field(description="Rule identifier")
    target_id_card: str = Field(description="Target person id card")
    target: str = Field(description="Human-readable verification target")
    category: str = Field(description="Business category for the evidence")
    sql: str = Field(description="Executed SQL text")
    result_raw: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Raw query rows",
    )
    result_summary: str = Field(description="Human-readable evidence summary")
    time_range: str | None = Field(default=None, description="Optional time range")
    supports_conclusion: bool | None = Field(
        default=None,
        description="True/False when retrieval can decide, else None",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Evidence confidence",
    )
    exec_status: Literal["success", "no_data", "failed", "field_missing"] = Field(
        description="Execution status for this evidence item"
    )
    diagnostic_code: DiagnosticCode = Field(default="ok", description="Normalized diagnostic code")
    diagnostic_label: str = Field(default="查询成功", description="Human-readable diagnostic label")
    diagnostic_detail: str = Field(default="", description="Detailed diagnostic description")
    diagnostic_hint: str = Field(default="", description="Suggested troubleshooting hint")
    manual_verified: bool = Field(default=False, description="Whether this is manually verified high-priority evidence")
    manual_stance: str | None = Field(default=None, description="Manual review stance: support/refute")
    created_at: datetime = Field(default_factory=datetime.now)


class EvidenceBundle(BaseModel):
    """All evidence collected for one target person."""

    id_card: str
    collected_at: datetime = Field(default_factory=datetime.now)
    items: list[EvidenceItem] = Field(default_factory=list)

    @property
    def by_rule(self) -> dict[str, EvidenceItem]:
        return {item.rule_id: item for item in self.items}

    @property
    def success_count(self) -> int:
        return sum(1 for item in self.items if item.exec_status == "success")

    @property
    def failed_rules(self) -> list[str]:
        return [
            item.rule_id
            for item in self.items
            if item.exec_status in ("failed", "field_missing")
        ]
