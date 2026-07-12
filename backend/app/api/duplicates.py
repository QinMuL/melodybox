"""去重管理路由 /api/duplicates。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import load_organize_config
from app.database import SessionLocal, get_db
from app.models import DuplicateGroup, OrganizeTask
from app.schemas import (
    DuplicateGroupItem,
    DuplicateGroupListResponse,
    DuplicateGroupResponse,
    ResolveDuplicateRequest,
    StartTaskResponse,
)
from app.services import duplicate_service
from app.services.task_manager import task_manager

router = APIRouter(prefix="/duplicates", tags=["duplicates"])


@router.post("/scan", response_model=StartTaskResponse)
def scan_duplicates(db: Session = Depends(get_db)) -> StartTaskResponse:
    """扫描重复文件，返回 taskId。"""
    config = load_organize_config()
    input_dir = config.get("inputDir", "/music")
    exclude_patterns = config.get("excludePatterns", [])

    task = OrganizeTask(
        task_type="scan_duplicates",
        status="pending",
        progress=0.0,
        total_files=0,
        processed_files=0,
        config={"inputDir": input_dir, "excludePatterns": exclude_patterns},
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    task_manager.start_task(
        task.id,
        duplicate_service.run_duplicate_scan_task(
            task.id, input_dir, exclude_patterns, SessionLocal
        ),
    )
    return StartTaskResponse(taskId=task.id, status=task.status)


@router.get("/groups", response_model=DuplicateGroupListResponse)
def list_groups(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DuplicateGroupListResponse:
    """获取重复组列表。"""
    groups, total = duplicate_service.get_groups_with_files(db, page, pageSize)
    items = []
    for g in groups:
        items.append(DuplicateGroupResponse(
            id=g["id"],
            group_hash=g["group_hash"],
            similarity=g["similarity"],
            status=g["status"],
            detected_at=g["detected_at"],
            files=[DuplicateGroupItem(**f) for f in g["files"]],
        ))
    return DuplicateGroupListResponse(
        items=items, total=total, page=page, pageSize=pageSize,
    )


@router.post("/groups/{group_id}/resolve")
def resolve_group(
    group_id: str,
    req: ResolveDuplicateRequest,
    db: Session = Depends(get_db),
):
    """处理重复组（keepFileId, action: recycle|delete）。

    注意：group_id 参数实际为重复组标识（group_hash），用于定位组内所有成员。
    """
    config = load_organize_config()
    recycle_dir = config.get("recycleDir", "/music/.recycle")

    result = duplicate_service.resolve_group(
        db, group_id, req.keep_file_id, req.action, recycle_dir
    )
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return {
        "success": True,
        "message": "重复组已处理",
        "kept": result["kept"],
        "removed": result["removed"],
    }
