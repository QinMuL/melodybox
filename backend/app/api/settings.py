"""系统设置路由 /api/settings。"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.config import CONFIG_FILE, load_organize_config, save_organize_config, settings
from app.schemas import MessageResponse, SystemSettings, TestDirRequest, TestDirResponse
from app.utils.file_utils import ensure_dir, is_dir_accessible, is_dir_writable

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
    """获取系统配置。

    优先从持久化的 config.json 读取用户修改的目录路径，
    未修改的字段回退到环境变量默认值。
    """
    saved = load_organize_config()
    return SystemSettings(
        inputDir=saved.get("inputDir") or settings.MUSIC_INPUT_DIR,
        outputDir=saved.get("outputDir") or settings.MUSIC_OUTPUT_DIR,
        recycleDir=saved.get("recycleDir") or settings.MUSIC_RECYCLE_DIR,
        dbPath=settings.DB_PATH,
        logLevel=settings.LOG_LEVEL,
        supportedFormats=SUPPORTED_FORMATS,
        concurrency=4,
    )


@router.put("/", response_model=SystemSettings)
def update_settings(cfg: SystemSettings) -> SystemSettings:
    """更新系统配置。

    将目录配置持久化到 config.json，重启容器后仍生效。
    注意：环境变量级别的配置（如 LOG_LEVEL、DB_PATH）运行时不可变。
    """
    saved = load_organize_config()
    # 合并用户修改的目录字段到整理配置中
    saved["inputDir"] = cfg.inputDir
    saved["outputDir"] = cfg.outputDir
    saved["recycleDir"] = cfg.recycleDir
    save_organize_config(saved)

    # 自动创建回收站目录（如果用户指定了新路径）
    try:
        ensure_dir(cfg.recycleDir)
    except OSError:
        pass  # 创建失败不阻塞保存

    return SystemSettings(
        inputDir=cfg.inputDir,
        outputDir=cfg.outputDir,
        recycleDir=cfg.recycleDir,
        dbPath=settings.DB_PATH,
        logLevel=settings.LOG_LEVEL,
        supportedFormats=SUPPORTED_FORMATS,
        concurrency=cfg.concurrency,
    )


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
