"""FastAPI 应用入口。

启动时自动创建数据库表与默认配置，启用 CORS（允许所有来源，内网使用）。
监听 0.0.0.0:28081。
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import duplicates, library, organize, settings as settings_api, websocket
from app.config import settings
from app.database import init_db
from app.services.task_manager import task_manager

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("melodybox")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库与事件循环。"""
    logger.info("MelodyBox 启动中...")
    # 初始化数据库表
    init_db()
    logger.info("数据库已初始化: %s", settings.DB_PATH)
    # 记录事件循环，便于任务管理器提交协程
    task_manager.set_loop(asyncio.get_running_loop())
    logger.info("MelodyBox 已启动，监听 %s:%s", settings.HOST, settings.PORT)
    yield
    logger.info("MelodyBox 关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title="MelodyBox",
        description="音律盒子 - 音乐文件智能整理工具",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 启用 CORS（允许所有来源，内网使用）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由（统一 /api 前缀）
    app.include_router(library.router, prefix="/api")
    app.include_router(organize.router, prefix="/api")
    app.include_router(duplicates.router, prefix="/api")
    app.include_router(settings_api.router, prefix="/api")
    app.include_router(websocket.router, prefix="/api")

    # 健康检查
    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "service": "MelodyBox", "version": "0.1.0"}

    # 根路径
    @app.get("/", tags=["system"])
    def root() -> dict:
        return {"service": "MelodyBox", "docs": "/docs"}

    return app


# 模块级应用实例（uvicorn app.main:app 引用）
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL,
    )
