"""
settings.py — 全局配置加载
使用 pydantic-settings 从 config/.env 文件中读取所有配置项。
整个项目通过 `from config.settings import settings` 获取配置，不直接读 os.environ。
"""
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 文件路径（相对于项目根目录）
ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----------------------------------------------------------
    # LLM 配置
    # ----------------------------------------------------------
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    llm_timeout_seconds: float = 120.0
    rag_review_enabled: bool = False
    rag_review_api_key: str = ""
    rag_review_base_url: str = "https://api.deepseek.com/v1"
    rag_review_model: str = "deepseek-chat"

    # ----------------------------------------------------------
    # 数据库配置
    # ----------------------------------------------------------
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "bysj_t2s"
    db_charset: str = "utf8mb4"

    # ----------------------------------------------------------
    # 系统运行参数
    # ----------------------------------------------------------
    system_date: str = "2026-03-21"
    debate_max_rounds: int = 2
    consensus_threshold: float = 0.8
    log_level: str = "INFO"

    # ----------------------------------------------------------
    # 衍生属性（不来自 .env）
    # ----------------------------------------------------------
    @property
    def db_url(self) -> str:
        """SQLAlchemy 连接字符串"""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset={self.db_charset}"
        )

    @property
    def use_openai_compat(self) -> bool:
        """是否使用 OpenAI 兼容模式（非 Anthropic 的所有提供商）"""
        return self.llm_provider != "anthropic"

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"openai", "deepseek", "dashscope", "zhipu", "anthropic", "nova"}
        if v not in allowed:
            raise ValueError(f"LLM_PROVIDER 必须是 {allowed} 之一，当前值: {v}")
        return v

    def get_effective_base_url(self) -> str | None:
        """
        返回有效的 base_url：
        - openai 且留空 → None（走 OpenAI 官方默认）
        - 其他提供商的预设地址
        """
        if self.llm_base_url:
            return self.llm_base_url
        defaults = {
            "deepseek": "https://api.deepseek.com/v1",
            "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "zhipu":    "https://open.bigmodel.cn/api/paas/v4",
            "nova":     "https://once.novai.su/v1",   # Nova AI 中转 API
        }
        return defaults.get(self.llm_provider)


# 全局单例，整个项目统一从这里取配置
settings = Settings()
