"""系统设置路由 /api/settings。"""
from __future__ import annotations

import os

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas import MessageResponse, SystemSettings, TestDirRequest, TestDirResponse
from app.utils.file_utils import is_dir_accessible, is_dir_writable

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=SystemSettings)
def get_settings() -> SystemSettings:
    """获取系统配置。"""
    return SystemSettings(
        inputDir=settings.MUSIC_INPUT_DIR,
        outputDir=settings.MUSIC_OUTPUT_DIR,
        recycleDir=settings.MUSIC_RECYCLE_DIR,
        dbPath=settings.DB_PATH,
        logLevel=settings.LOG_LEVEL,
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
    """测试目录访问权限（可读/可写）。"""
    path = req.path
    accessible = is_dir_accessible(path)
    writable = is_dir_writable(path) if accessible else False
    if not accessible:
        return TestDirResponse(
            accessible=False,
            writable=False,
            message=f"目录不可访问: {path}",
        )
    if not writable:
        return TestDirResponse(
            accessible=True,
            writable=False,
            message=f"目录可读但不可写: {path}",
        )
    return TestDirResponse(
        accessible=True,
        writable=True,
        message=f"目录可读写: {path}",
    )
