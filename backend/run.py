"""MelodyBox 开发启动脚本。

可通过 `python run.py` 直接启动开发服务器，
也可使用 `uvicorn app.main:app --host 0.0.0.0 --port 28081`。
"""
import uvicorn

from app.config import settings


def main() -> None:
    """启动 FastAPI 应用。"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL,
    )


if __name__ == "__main__":
    main()
