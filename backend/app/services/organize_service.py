"""文件整理业务逻辑。

扫描输入目录、读取元数据、按命名模板渲染新文件名，
将文件按"艺术家/专辑/歌曲"结构移动或复制。
使用 asyncio + ThreadPoolExecutor 实现非阻塞任务。
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models import OrganizeTask, TaskLog
from app.schemas import PreviewItem
from app.services import metadata_service
from app.services.task_manager import (
    MSG_ERROR,
    task_manager,
)
from app.utils.file_utils import (
    copy_file,
    find_audio_files,
    is_audio_file,
    move_file,
    unique_path,
)
from app.utils.naming import render_template

logger = logging.getLogger(__name__)

# 默认模板
DEFAULT_TEMPLATE = "{artist}/{album}/{track:02d}-{title}.{ext}"


def _build_render_data(metadata: Dict[str, Any], file_path: str) -> Dict[str, Any]:
    """构造模板渲染所需的数据字典。"""
    from app.utils.file_utils import get_audio_format

    return {
        "artist": metadata.get("artist") or "Unknown Artist",
        "album": metadata.get("album") or "Unknown Album",
        "title": metadata.get("title") or "Unknown Title",
        "track_number": metadata.get("track_number"),
        "year": metadata.get("year"),
        "ext": get_audio_format(file_path) or "mp3",
    }


def _decide_target(
    source: str,
    target_rel: str,
    output_dir: str,
    move: bool,
    policy: str,
) -> tuple[str, str, str | None]:
    """根据冲突策略决定最终目标路径与动作。

    Returns:
        (final_target, action, reason)
    """
    import os

    target = os.path.join(output_dir, target_rel)
    action = "move" if move else "copy"

    if not os.path.exists(target):
        return target, action, None

    # 目标已存在，按策略处理
    if policy == "skip":
        return target, "skip", "目标文件已存在（skip）"
    if policy == "overwrite":
        return target, action, None  # 调用方负责覆盖
    # rename：生成不冲突路径
    target_path = unique_path(type(target)(target))
    return str(target_path), action, "目标已存在，重命名"


def preview(
    input_dir: str,
    output_dir: str,
    naming_template: str = DEFAULT_TEMPLATE,
    move: bool = False,
    policy: str = "skip",
    exclude_patterns: List[str] | None = None,
) -> List[PreviewItem]:
    """预览整理结果（dry-run，不实际操作文件）。

    Returns:
        PreviewItem 列表
    """
    items: List[PreviewItem] = []
    files = find_audio_files(input_dir, exclude_patterns)
    template = naming_template or DEFAULT_TEMPLATE

    for file_path in files:
        metadata = metadata_service.read_metadata(file_path)
        data = _build_render_data(metadata, file_path)
        target_rel = render_template(template, data)
        final_target, action, reason = _decide_target(
            file_path, target_rel, output_dir, move, policy
        )
        items.append(
            PreviewItem(
                source=file_path,
                target=final_target,
                action=action,
                reason=reason,
                artist=data["artist"],
                album=data["album"],
                title=data["title"],
                track_number=data["track_number"],
            )
        )
    return items


def _process_single_file(
    source: str,
    target: str,
    action: str,
    move: bool,
    policy: str,
) -> tuple[str, str | None]:
    """在执行器线程中处理单个文件。

    Returns:
        (final_target, error_message)
    """
    import os

    try:
        if action == "skip":
            return target, None

        # 目标存在时的覆盖处理
        if os.path.exists(target):
            if policy == "skip":
                return target, None
            if policy == "overwrite":
                # 删除已存在的目标
                try:
                    os.remove(target)
                except OSError:
                    pass
            # rename 策略已由 _decide_target 生成新路径

        if move:
            move_file(source, target)
        else:
            copy_file(source, target)
        return target, None
    except Exception as exc:  # noqa: BLE001
        return target, str(exc)


async def run_organize_task(
    task_id: str,
    config: Dict[str, Any],
    db_session_factory,
) -> Dict[str, Any]:
    """执行整理任务的异步协程。

    Args:
        task_id: 任务 ID
        config: 整理配置字典
        db_session_factory: 返回新数据库会话的可调用对象

    Returns:
        任务结果字典
    """
    input_dir = config.get("inputDir") or config.get("input_dir") or ""
    output_dir = config.get("outputDir") or config.get("output_dir") or ""
    template = config.get("namingTemplate") or DEFAULT_TEMPLATE
    move = bool(config.get("moveInsteadOfCopy", config.get("move", False)))
    policy = config.get("overwritePolicy", config.get("overwrite_policy", "skip"))
    exclude_patterns = config.get("excludePatterns") or []

    moved = 0
    copied = 0
    skipped = 0
    failed = 0

    # 扫描文件（同步，通常较快）
    files = find_audio_files(input_dir, exclude_patterns)
    total = len(files)

    db = db_session_factory()
    try:
        # 更新任务记录初始状态
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "running"
            task.started_at = datetime.utcnow()
            task.total_files = total
            task.processed_files = 0
            task.progress = 0.0
            db.commit()

        await task_manager.update_progress(
            task_id,
            progress=0.0,
            total_files=total,
            processed_files=0,
            current_file=None,
        )
        await task_manager.send_log(task_id, "info", f"开始整理任务，共 {total} 个文件")

        # 使用线程池执行阻塞的文件 IO
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=4) as executor:
            for idx, file_path in enumerate(files, start=1):
                # 读取元数据
                metadata = await loop.run_in_executor(
                    executor, metadata_service.read_metadata, file_path
                )
                data = _build_render_data(metadata, file_path)
                target_rel = render_template(template, data)
                final_target, action, reason = _decide_target(
                    file_path, target_rel, output_dir, move, policy
                )

                # 执行文件操作
                final_target, err = await loop.run_in_executor(
                    executor,
                    _process_single_file,
                    file_path,
                    final_target,
                    action,
                    move,
                    policy,
                )

                if err is not None:
                    failed += 1
                    await task_manager.send_log(
                        task_id, "error", f"处理失败 {file_path}: {err}"
                    )
                    db.add(TaskLog(
                        task_id=task_id, level="error",
                        message=f"处理失败 {file_path}: {err}",
                    ))
                elif action == "skip":
                    skipped += 1
                elif action == "move":
                    moved += 1
                else:
                    copied += 1

                # 更新进度
                progress = (idx / total * 100) if total else 100.0
                await task_manager.update_progress(
                    task_id,
                    progress=progress,
                    total_files=total,
                    processed_files=idx,
                    current_file=file_path,
                )

                # 持久化进度（每处理一个文件更新一次）
                if task is not None:
                    task.processed_files = idx
                    task.progress = progress
                    task.current_file = file_path
                    db.commit()

        # 任务完成
        result = {
            "moved": moved,
            "copied": copied,
            "skipped": skipped,
            "failed": failed,
            "total": total,
        }
        if task is not None:
            task.status = "completed"
            task.progress = 100.0
            task.processed_files = total
            task.current_file = None
            task.completed_at = datetime.utcnow()
            task.result = result
            db.commit()
        await task_manager.send_log(
            task_id, "info",
            f"整理完成：移动 {moved}，复制 {copied}，跳过 {skipped}，失败 {failed}",
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("整理任务异常: %s", task_id)
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.result = {"error": str(exc)}
            db.commit()
        db.add(TaskLog(task_id=task_id, level="error", message=f"任务异常: {exc}"))
        db.commit()
        await task_manager._publish(task_id, {
            "type": MSG_ERROR, "data": {"message": str(exc)}
        })
        raise
    finally:
        db.close()
