"""SQLAlchemy 数据库连接与初始化。"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import ensure_data_dir, settings

# 确保数据目录存在
ensure_data_dir()

# SQLite 引擎（check_same_thread=False 以支持 FastAPI 异步场景下的线程访问）
engine = create_engine(
    f"sqlite:///{settings.DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类
Base = declarative_base()


def init_db() -> None:
    """创建所有数据表（启动时调用）。"""
    # 必须先导入模型，确保表定义被加载
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖：提供数据库会话并自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
