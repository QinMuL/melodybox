"""系统设置路由 /api/settings。"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas import MessageResponse, SystemSettings, TestDirRequest, TestDirResponse
from app.utils.file_utils import is_dir_accessible, is_dir_writable

router = APIRouter(prefix="/settings", tags=["settings"])

# 支持的音频格式（与 file_utils.AUDIO_EXTENSIONS 一致）
SUPPORTED_FORMATS = [".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac", ".wma", ".ape"]
# 测试目录时统计的音频扩展名集合
_AUDIO_EXTS = {e.lower() for e in SUPPORTED_FORMATS}


def _count_audio_files(directory: str, limit: int = 10000) -> int:
    """统计目录下音频文件数量（限制上限避免大目录卡顿）。"""
    root = Path(directory)
    count = 0
    try:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in _AUDIO_EXTS:
                count += 1
                if count >= limit:
                    break
    except (OSError, PermissionError):
        pass
    return count


@router.get("/", response_model=SystemSettings)
def get_settings() -> SystemSettings:
    """获取系统配置。"""
    return SystemSettings(
        inputDir=settings.MUSIC_INPUT_DIR,
        outputDir=settings.MUSIC_OUTPUT_DIR,
        recycleDir=settings.MUSIC_RECYCLE_DIR,
        dbPath=settings.DB_PATH,
        logLevel=settings.LOG_LEVEL,
        supportedFormats=SUPPORTED_FORMATS,
        concurrency=4,
    )


@router.put("/", response_model=SystemSettings)
def update_settings(cfg: SystemSettings) -> SystemSettings:
    """更新系统配置。

    注意：环境变量在运行时不可变，此接口仅返回当前生效配置。
    如需持久化运行时配置，请使用整理配置接口 /api/organize/config。
    """
    return cfg


@router.post("/test-dir", response_model=TestDirResponse)
def test_dir(req: TestDirRequest) -> TestDirResponse:
    """测试目录访问权限（可读/可写）并统计音频文件数。"""
    path = req.path
    accessible = is_dir_accessible(path)
    if not accessible:
        return TestDirResponse(
            accessible=False,
            writable=False,
            message=f"目录不可访问: {path}",
            fileCount=0,
        )
    writable = is_dir_writable(path)
    file_count = _count_audio_files(path)
    if not writable:
        return TestDirResponse(
            accessible=True,
            writable=False,
            message=f"目录可读但不可写（含 {file_count} 个音频文件）",
            fileCount=file_count,
        )
    return TestDirResponse(
        accessible=True,
        writable=True,
        message=f"目录可读写（含 {file_count} 个音频文件）",
        fileCount=file_count,
    )
