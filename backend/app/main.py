"""FastAPI 应用入口。

启动时自动创建数据库表与默认配置，启用 CORS（允许所有来源，内网使用）。
监听 0.0.0.0:28081。
"""
from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import duplicates, library, logs, organize, settings as settings_api, websocket
from app.config import settings, DATA_DIR
from app.database import init_db
from app.services.task_manager import task_manager

# 配置日志：同时输出到 stdout 和文件（轮转 10MB × 5 份）
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_LEVEL = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

# 确保日志目录存在
_LOG_DIR = DATA_DIR / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "melodybox.log"

# 根日志配置
_root = logging.getLogger()
_root.setLevel(_LOG_LEVEL)
# 清理默认 handler
for _h in list(_root.handlers):
    _root.removeHandler(_h)
# stdout handler（Docker 收集）
_stream = logging.StreamHandler()
_stream.setFormatter(logging.Formatter(_LOG_FORMAT))
_root.addHandler(_stream)
# 文件 handler（轮转：10MB × 5 份，UTF-8）
_file = RotatingFileHandler(
    _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file.setFormatter(logging.Formatter(_LOG_FORMAT))
_root.addHandler(_file)

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
    app.include_router(logs.router, prefix="/api")
    app.include_router(websocket.router, prefix="/api")

    # 健康检查
    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "service": "MelodyBox", "version": "0.1.0"}

    # 根路径
    @app.get("/", tags=["system"])
    def root() -> dict:
        return {"service": "MelodyBox", "docs": "/docs"}

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request, call_next):
        response = await call_next(request)
        # 只记录 API 请求（排除静态文件和健康检查）
        path = request.url.path
        if path.startswith("/api/") and path != "/api/logs/":
            logger.info(
                "%s %s -> %s",
                request.method, path, response.status_code,
            )
        return response

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
