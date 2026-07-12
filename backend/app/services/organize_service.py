"""文件整理业务逻辑。

支持两种独立操作：
1. rename（文件命名）：基于元数据重命名文件，不移动位置。格式：艺术家 - 歌曲名.扩展名
2. organize（文件整理）：按 艺术家/专辑/ 结构归类移动文件，不改文件名。

使用 asyncio + ThreadPoolExecutor 实现非阻塞任务。
"""
from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models import OrganizeTask, TaskLog
from app.schemas import CompanionFile, PreviewItem
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

# 命名模板（rename 模式）：只改文件名，不创建子目录
RENAME_TEMPLATE = "{artist} - {title}.{ext}"
# 整理模板（organize 模式）：按艺术家/专辑/归类，保留原文件名
ORGANIZE_TEMPLATE = "{artist}/{album}/{filename}"

# 音频文件的附属文件后缀（移动/重命名时一并处理）
COMPANION_SUFFIXES = ["-mediainfo.json"]


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
        "filename": os.path.basename(file_path),  # 原文件名（organize 模式保留）
    }


def _find_companion_files(file_path: str) -> List[str]:
    """查找与音频文件同名的附属文件（如 song-mediainfo.json）。

    音频文件 /path/to/song.flac 对应附属文件：
    /path/to/song-mediainfo.json
    """
    stem, _ = os.path.splitext(file_path)
    companions: List[str] = []
    for suffix in COMPANION_SUFFIXES:
        companion_path = f"{stem}{suffix}"
        if os.path.exists(companion_path):
            companions.append(companion_path)
    return companions


def _compute_companion_target(
    companion_path: str,
    source_audio: str,
    target_audio: str,
    mode: str,
) -> str:
    """计算附属文件的目标路径。

    rename 模式：用音频文件的新 stem + 附属后缀
      源：/dir/artist - song.flac           目标：/dir/newartist - new song.flac
      附属：/dir/artist - song-mediainfo.json → /dir/newartist - new song-mediainfo.json

    organize 模式：移动到音频目标目录，保留原附属文件名
      源：/music/artist - song.flac         目标：/music/artist/album/artist - song.flac
      附属：/music/artist - song-mediainfo.json → /music/artist/album/artist - song-mediainfo.json
    """
    if mode == "rename":
        target_stem = os.path.splitext(target_audio)[0]
        audio_stem = os.path.splitext(source_audio)[0]
        companion_suffix = companion_path[len(audio_stem):]
        return f"{target_stem}{companion_suffix}"
    else:
        target_dir = os.path.dirname(target_audio)
        companion_name = os.path.basename(companion_path)
        return os.path.join(target_dir, companion_name)


def _cleanup_empty_dirs(root_dir: str) -> int:
    """清理目录树中的空子目录，返回清理数量。"""
    removed = 0
    root = Path(root_dir)
    if not root.exists():
        return 0
    # 从最深的目录开始检查（postorder 遍历）
    for dirpath, dirnames, filenames in sorted(
        os.walk(root_dir, topdown=False),
        key=lambda x: -len(Path(x[0]).parts),
    ):
        if Path(dirpath) == root:
            continue
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                removed += 1
        except OSError:
            pass
    return removed


def _compute_target(
    file_path: str,
    metadata: Dict[str, Any],
    mode: str,
    output_dir: str,
    naming_template: str | None = None,
) -> str:
    """根据模式计算目标路径。

    Args:
        file_path: 源文件路径
        metadata: 元数据字典
        mode: "rename"（只重命名）或 "organize"（只归类移动）
        output_dir: 输出根目录
        naming_template: 自定义模板（可选）

    Returns:
        目标文件绝对路径
    """
    data = _build_render_data(metadata, file_path)

    if mode == "rename":
        # rename 模式：在原目录中重命名，不移动
        template = naming_template or RENAME_TEMPLATE
        new_name = render_template(template, data)
        # 新文件名可能包含子目录分隔符，取 basename
        new_name = os.path.basename(new_name)
        return os.path.join(os.path.dirname(file_path), new_name)
    else:
        # organize 模式：移动到 艺术家/专辑/ 下，保留原文件名
        template = naming_template or ORGANIZE_TEMPLATE
        target_rel = render_template(template, data)
        return os.path.join(output_dir, target_rel)


def _decide_target(
    source: str,
    target: str,
    move: bool,
    policy: str,
) -> tuple[str, str, str | None]:
    """根据冲突策略决定最终目标路径与动作。

    Args:
        source: 源文件路径
        target: 计算出的目标路径
        move: 是否移动（True=move，False=copy）
        policy: 冲突策略 skip/overwrite/rename

    Returns:
        (final_target, action, reason)
    """
    # 源和目标相同，跳过
    if os.path.abspath(source) == os.path.abspath(target):
        return target, "skip", "文件名已符合规范"

    action = "move" if move else "copy"

    if not os.path.exists(target):
        return target, action, None

    # 目标已存在，按策略处理
    if policy == "skip":
        return target, "skip", "目标文件已存在（skip）"
    if policy == "overwrite":
        return target, action, None
    # rename 策略：生成不冲突路径
    target_path = unique_path(type(target)(target))
    return str(target_path), action, "目标已存在，自动重命名"


def preview(
    input_dir: str,
    output_dir: str,
    mode: str = "organize",
    naming_template: str | None = None,
    move: bool = False,
    policy: str = "skip",
    exclude_patterns: List[str] | None = None,
) -> List[PreviewItem]:
    """预览整理结果（dry-run，不实际操作文件）。

    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        mode: "rename"（只重命名）或 "organize"（只归类移动）
        naming_template: 自定义命名模板
        move: True=移动，False=复制
        policy: 冲突策略 skip/overwrite/rename
        exclude_patterns: 排除模式列表

    Returns:
        PreviewItem 列表
    """
    items: List[PreviewItem] = []
    files = find_audio_files(input_dir, exclude_patterns)

    for file_path in files:
        metadata = metadata_service.read_metadata(file_path)
        data = _build_render_data(metadata, file_path)
        target = _compute_target(
            file_path, metadata, mode, output_dir, naming_template
        )
        final_target, action, reason = _decide_target(
            file_path, target, move, policy
        )
        # 查找附属文件并计算目标路径
        companions = [
            CompanionFile(
                old_path=c,
                new_path=_compute_companion_target(c, file_path, final_target, mode),
            )
            for c in _find_companion_files(file_path)
        ]
        items.append(
            PreviewItem(
                old_path=file_path,
                new_path=final_target,
                action=action,
                reason=reason,
                artist=data["artist"],
                album=data["album"],
                title=data["title"],
                track_number=data["track_number"],
                companions=companions,
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
    try:
        if action == "skip":
            return target, None

        # 确保目标目录存在
        os.makedirs(os.path.dirname(target), exist_ok=True)

        # 目标存在时的覆盖处理
        if os.path.exists(target):
            if policy == "skip":
                return target, None
            if policy == "overwrite":
                try:
                    os.remove(target)
                except OSError:
                    pass

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
        config: 整理配置字典，需包含 mode 字段（"rename" 或 "organize"）
        db_session_factory: 返回新数据库会话的可调用对象

    Returns:
        任务结果字典
    """
    input_dir = config.get("inputDir") or config.get("input_dir") or ""
    output_dir = config.get("outputDir") or config.get("output_dir") or ""
    mode = config.get("mode", "organize")  # rename 或 organize
    # 模式默认模板：rename 用扁平文件名，organize 用目录结构。不使用 config 中保存的旧模板。
    naming_template = config.get("namingTemplate")
    if mode == "rename":
        naming_template = naming_template or RENAME_TEMPLATE
    else:
        naming_template = naming_template or ORGANIZE_TEMPLATE
    move = bool(config.get("moveInsteadOfCopy", config.get("move", False)))
    policy = config.get("overwritePolicy", config.get("overwrite_policy", "skip"))
    exclude_patterns = config.get("excludePatterns") or []

    moved = 0
    copied = 0
    skipped = 0
    failed = 0

    # 扫描文件
    files = find_audio_files(input_dir, exclude_patterns)
    total = len(files)

    action_desc = "重命名" if mode == "rename" else "整理归类"
    logger.info("开始%s任务，共 %d 个文件", action_desc, total)

    db = db_session_factory()
    try:
        # 更新任务记录初始状态
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "running"
            task.started_at = datetime.now()
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
        await task_manager.send_log(
            task_id, "info", f"开始{action_desc}任务，共 {total} 个文件"
        )

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=4) as executor:
            for idx, file_path in enumerate(files, start=1):
                # 读取元数据
                metadata = await loop.run_in_executor(
                    executor, metadata_service.read_metadata, file_path
                )
                # 计算目标路径
                target = _compute_target(
                    file_path, metadata, mode, output_dir, naming_template
                )
                final_target, action, reason = _decide_target(
                    file_path, target, move, policy
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

                # 处理附属文件（如 -mediainfo.json）
                companions_processed = 0
                if err is None and action != "skip":
                    for companion in _find_companion_files(file_path):
                        companion_target = _compute_companion_target(
                            companion, file_path, final_target, mode
                        )
                        ct, ca, _ = _decide_target(
                            companion, companion_target, move, policy
                        )
                        _, ce = await loop.run_in_executor(
                            executor,
                            _process_single_file,
                            companion,
                            ct,
                            ca,
                            move,
                            policy,
                        )
                        if ce:
                            logger.warning("附属文件处理失败 %s: %s", companion, ce)
                        else:
                            companions_processed += 1

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
                    await task_manager.send_log(
                        task_id, "info", f"跳过 {file_path}：{reason}"
                    )
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

                # 持久化进度
                if task is not None:
                    task.processed_files = idx
                    task.progress = progress
                    task.current_file = file_path
                    db.commit()

        # 清理空目录（仅 move 模式，copy 保留原文件不产生空目录）
        dirs_cleaned = 0
        if move and moved > 0:
            dirs_cleaned = _cleanup_empty_dirs(input_dir)
            if dirs_cleaned > 0:
                await task_manager.send_log(
                    task_id, "info", f"清理空目录 {dirs_cleaned} 个"
                )
                logger.info("清理空目录 %d 个", dirs_cleaned)

        # 任务完成
        result = {
            "mode": mode,
            "moved": moved,
            "copied": copied,
            "skipped": skipped,
            "failed": failed,
            "total": total,
            "dirsCleaned": dirs_cleaned,
        }
        if task is not None:
            task.status = "completed"
            task.progress = 100.0
            task.processed_files = total
            task.current_file = None
            task.completed_at = datetime.now()
            task.result = result
            db.commit()
        await task_manager.send_log(
            task_id, "info",
            f"{action_desc}完成：移动 {moved}，复制 {copied}，跳过 {skipped}，失败 {failed}，清理空目录 {dirs_cleaned}",
        )
        logger.info("%s任务完成: 移动=%d 复制=%d 跳过=%d 失败=%d 清理空目录=%d",
                    action_desc, moved, copied, skipped, failed, dirs_cleaned)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("%s任务异常: %s", action_desc, task_id)
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "failed"
            task.completed_at = datetime.now()
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
