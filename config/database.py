"""
database.py — 数据库连接管理
提供 SQLAlchemy Engine 和 Session 工厂。
使用方式：
    from config.database import get_session
    with get_session() as session:
        result = session.execute(text("SELECT 1"))
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from config.settings import settings

# 创建 Engine（连接池，整个应用共享一个）
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,       # 每次使用连接前 ping，自动重连
    pool_size=5,
    max_overflow=10,
    echo=False,               # 设为 True 可打印所有 SQL（调试用）
)

# Session 工厂
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    上下文管理器，提供带自动提交/回滚的 Session。
    用法：
        with get_session() as session:
            rows = session.execute(text("SELECT ..."), {"id_card": "..."}).fetchall()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database() -> bool:
    """
    冒烟测试：验证数据库连接是否正常。
    返回 True 表示连接成功。
    """
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        logger.info(f"✅ 数据库连接成功：{settings.db_host}:{settings.db_port}/{settings.db_name}")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接失败：{e}")
        return False
