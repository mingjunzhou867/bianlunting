from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RagChunk(BaseModel):
    """本地RAG管道使用的分块负载"""

    chunk_id: int = Field(description="源文档中中的分块序列号，从1开始")
    doc_id: int = Field(description="导入时分配的文档序列号，从1开始")
    title: str = Field(description="政策或文档标题")
    belong_id: str = Field(description="政策或文档中的结构化章节或文章ID")
    context: str = Field(description="此分块的原始政策文本")

    @field_validator("chunk_id", "doc_id")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("chunk_id and doc_id 必须是正整数")
        return value

    @field_validator("title", "belong_id", "context")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title, belong_id and context 不能为空")
        return normalized
