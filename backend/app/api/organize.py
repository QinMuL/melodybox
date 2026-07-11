"""整理任务路由 /api/organize。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import load_organize_config, save_organize_config
from app.database import SessionLocal, get_db
from app.models import OrganizeTask
from app.schemas import (
    OrganizeConfig,
    PreviewItem,
    PreviewRequest,
    PreviewResponse,
    StartTaskRequest,
    StartTaskResponse,
    TaskListResponse,
    TaskStatusResponse,
)
from app.services import organize_service
from app.services.task_manager import task_manager

router = APIRouter(prefix="/organize", tags=["organize"])


@router.get("/config", response_model=OrganizeConfig)
def get_organize_config() -> OrganizeConfig:
    """获取整理配置。"""
    config = load_organize_config()
    return OrganizeConfig(**config)


@router.put("/config", response_model=OrganizeConfig)
def update_organize_config(config: OrganizeConfig) -> OrganizeConfig:
    """更新整理配置（持久化到 config.json）。"""
    save_organize_config(config.model_dump())
    return config


@router.post("/preview", response_model=PreviewResponse)
def preview(req: PreviewRequest, db: Session = Depends(get_db)) -> PreviewResponse:
    """预览整理结果（dryRun，不实际操作文件）。"""
    saved = load_organize_config()
    input_dir = req.inputDir or saved["inputDir"]
    output_dir = req.outputDir or saved["outputDir"]
    template = req.namingTemplate or saved["namingTemplate"]
    move = req.moveInsteadOfCopy if req.moveInsteadOfCopy is not None else saved["moveInsteadOfCopy"]
    policy = req.overwritePolicy or saved["overwritePolicy"]
    exclude_patterns = req.excludePatterns if req.excludePatterns is not None else saved["excludePatterns"]

    items: list[PreviewItem] = organize_service.preview(
        input_dir=input_dir,
        output_dir=output_dir,
        naming_template=template,
        move=move,
        policy=policy,
        exclude_patterns=exclude_patterns,
    )
    skipped = sum(1 for i in items if i.action == "skip")
    return PreviewResponse(items=items, total=len(items), skipped=skipped)


@router.post("/start", response_model=StartTaskResponse)
def start_task(req: StartTaskRequest, db: Session = Depends(get_db)) -> StartTaskResponse:
    """启动整理任务，返回 taskId。"""
    # 确定配置：优先使用请求中的配置，否则用已保存配置
    if req.config is not None:
        config = req.config.model_dump()
    else:
        config = load_organize_config()

    # 创建任务记录
    task = OrganizeTask(
        task_type="organize",
        status="pending",
        progress=0.0,
        total_files=0,
        processed_files=0,
        config=config,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 启动后台任务
    task_manager.start_task(
        task.id,
        organize_service.run_organize_task(task.id, config, SessionLocal),
    )
    return StartTaskResponse(taskId=task.id, status=task.status)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskStatusResponse:
    """获取任务状态。"""
    task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatusResponse.model_validate(task)


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TaskListResponse:
    """获取任务列表。"""
    query = db.query(OrganizeTask).order_by(OrganizeTask.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * pageSize).limit(pageSize).all()
    return TaskListResponse(
        items=[TaskStatusResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        pageSize=pageSize,
    )
