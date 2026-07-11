"""去重检测业务逻辑。

两级去重：
1. 第一级：按 file_hash（MD5）精确匹配，相似度 100
2. 第二级：按元数据（artist+title+duration±3秒）模糊匹配

对每组重复文件，推荐保留音质最高（bitrate 最高，其次文件最大）的文件。
处理时将非保留文件移到回收站目录。
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import DuplicateGroup, OrganizeTask, Song, TaskLog, normalize_name
from app.services import metadata_service, scan_service
from app.services.task_manager import MSG_ERROR, task_manager
from app.utils.file_utils import (
    compute_file_hash,
    delete_file,
    file_size,
    find_audio_files,
    move_to_recycle,
)

logger = logging.getLogger(__name__)

# 模糊匹配的时长容忍度（秒）
DURATION_TOLERANCE = 3.0


def _make_fuzzy_key(metadata: Dict[str, Any], duration: Optional[float]) -> str:
    """构造模糊匹配键：标准化艺术家+标题，忽略时长差异。"""
    artist = normalize_name(metadata.get("artist") or "")
    title = normalize_name(metadata.get("title") or "")
    # 时长按 3 秒分桶，便于将相近时长的归为一组
    dur_bucket = ""
    if duration and duration > 0:
        dur_bucket = str(int(duration // DURATION_TOLERANCE))
    return f"{artist}||{title}||{dur_bucket}"


def _duration_similarity(d1: Optional[float], d2: Optional[float]) -> float:
    """根据时长差异计算相似度（0-100）。"""
    if not d1 or not d2:
        return 80.0
    diff = abs(d1 - d2)
    if diff == 0:
        return 100.0
    if diff >= DURATION_TOLERANCE:
        # 差异越大分数越低
        return max(0.0, 100.0 - diff * 10)
    return 100.0 - (diff / DURATION_TOLERANCE) * 20.0


def _recommend_keep(songs: List[Song]) -> str:
    """从一组歌曲中推荐保留的（bitrate 最高，其次文件最大）。"""
    if not songs:
        return ""

    def _score(s: Song) -> tuple:
        # 元组比较：先比 bitrate，再比 file_size
        bitrate = s.bitrate or 0
        size = s.file_size or 0
        return (bitrate, size)

    best = max(songs, key=_score)
    return best.id


def _clear_existing_groups(db: Session) -> None:
    """清空旧的重复组记录（重新扫描前调用）。"""
    db.query(DuplicateGroup).delete()
    db.commit()


def detect_duplicates(
    db: Session,
    directory: str,
    exclude_patterns: Optional[List[str]] = None,
    on_progress=None,
) -> Dict[str, Any]:
    """检测重复文件并写入 duplicate_groups 表。

    Args:
        db: 数据库会话
        directory: 扫描目录
        exclude_patterns: 排除模式
        on_progress: 进度回调 (processed, total, current_file)

    Returns:
        包含 groups（重复组数）、duplicates（重复文件数）的字典
    """
    # 重新扫描并索引（确保 songs 表是最新的，并计算 hash）
    logger.info("去重扫描：重新索引文件并计算哈希...")
    scan_service.scan_directory(
        db, directory, exclude_patterns, compute_hash=True,
        on_progress=on_progress,
    )

    _clear_existing_groups(db)

    # 取出所有歌曲
    songs = db.query(Song).all()
    logger.info("去重分析：共 %d 首歌曲", len(songs))

    # 第一级：按 file_hash 分组
    hash_groups: Dict[str, List[Song]] = defaultdict(list)
    for song in songs:
        if song.file_hash:
            hash_groups[song.file_hash].append(song)

    # 记录已分组歌曲 id
    grouped_song_ids: set[str] = set()
    group_count = 0
    duplicate_count = 0

    for hash_val, group in hash_groups.items():
        if len(group) < 2:
            continue
        group_hash = f"hash:{hash_val}"
        for song in group:
            db.add(DuplicateGroup(
                song_id=song.id,
                group_hash=group_hash,
                similarity=100.0,
                status="pending",
                detected_at=datetime.now(),
            ))
            grouped_song_ids.add(song.id)
        duplicate_count += len(group)
        group_count += 1

    # 第二级：对未在 hash 组中的歌曲，按模糊键分组
    # 这里对全部歌曲按模糊键分组（hash 组成员也可能参与，但已记录）
    fuzzy_groups: Dict[str, List[Song]] = defaultdict(list)
    fuzzy_meta: Dict[str, Dict[str, Any]] = {}

    for song in songs:
        # 读取元数据用于构造模糊键（从已索引的 song 字段推断）
        metadata = {
            "artist": _get_artist_name(db, song),
            "title": song.title,
        }
        key = _make_fuzzy_key(metadata, song.duration)
        fuzzy_groups[key].append(song)
        fuzzy_meta[key] = metadata

    for key, group in fuzzy_groups.items():
        if len(group) < 2:
            continue
        group_hash = f"fuzzy:{key}"
        for song in group:
            if song.id in grouped_song_ids:
                continue
            db.add(DuplicateGroup(
                song_id=song.id,
                group_hash=group_hash,
                similarity=_duration_similarity(
                    song.duration,
                    _group_avg_duration(group),
                ),
                status="pending",
                detected_at=datetime.now(),
            ))
            duplicate_count += 1
        group_count += 1

    db.commit()
    logger.info("去重完成：发现 %d 个重复组，%d 个重复文件", group_count, duplicate_count)
    return {"groups": group_count, "duplicates": duplicate_count}


def _group_avg_duration(songs: List[Song]) -> Optional[float]:
    """计算组内平均时长。"""
    durations = [s.duration for s in songs if s.duration]
    if not durations:
        return None
    return sum(durations) / len(durations)


def _get_artist_name(db: Session, song: Song) -> str:
    """通过歌曲的专辑获取艺术家名。"""
    from app.models import Album, Artist

    album = db.query(Album).filter(Album.id == song.album_id).first()
    if album is None:
        return "Unknown"
    artist = db.query(Artist).filter(Artist.id == album.artist_id).first()
    return artist.name if artist else "Unknown"


async def run_duplicate_scan_task(
    task_id: str,
    directory: str,
    exclude_patterns: Optional[List[str]],
    db_session_factory,
) -> Dict[str, Any]:
    """执行去重扫描的异步任务。"""
    db = db_session_factory()
    try:
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "running"
            task.started_at = datetime.now()
            task.progress = 0.0
            db.commit()

        await task_manager.send_log(task_id, "info", f"开始去重扫描: {directory}")

        def _progress(processed: int, total: int, current: str) -> None:
            if total <= 0:
                return
            progress = processed / total * 100
            # 更新内存进度（在 executor 线程中调用）
            task_manager._progress[task_id]["progress"] = progress
            task_manager._progress[task_id]["processed_files"] = processed
            task_manager._progress[task_id]["total_files"] = total
            task_manager._progress[task_id]["current_file"] = current
            # 同步更新数据库中的任务记录（前端轮询数据库查询进度）
            if task is not None:
                task.progress = progress
                task.processed_files = processed
                task.total_files = total
                task.current_file = current
                db.commit()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            detect_duplicates,
            db,
            directory,
            exclude_patterns,
            _progress,
        )

        if task is not None:
            task.status = "completed"
            task.progress = 100.0
            task.completed_at = datetime.now()
            task.result = result
            db.commit()
        await task_manager.send_log(
            task_id, "info",
            f"去重完成：发现 {result['groups']} 个重复组，{result['duplicates']} 个重复文件",
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("去重任务异常: %s", task_id)
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


def get_groups_with_files(
    db: Session, page: int, page_size: int
) -> tuple[List[Dict[str, Any]], int]:
    """获取重复组列表（含每组的文件信息）。

    Returns:
        (groups, total)
    """
    # 按 group_hash 聚合
    all_groups = db.query(DuplicateGroup).order_by(DuplicateGroup.detected_at.desc()).all()
    groups_map: Dict[str, List[DuplicateGroup]] = defaultdict(list)
    for g in all_groups:
        groups_map[g.group_hash].append(g)

    total = len(groups_map)
    group_hashes = list(groups_map.keys())
    start = (page - 1) * page_size
    end = start + page_size
    page_hashes = group_hashes[start:end]

    result: List[Dict[str, Any]] = []
    for gh in page_hashes:
        members = groups_map[gh]
        song_ids = [m.song_id for m in members]
        songs = db.query(Song).filter(Song.id.in_(song_ids)).all() if song_ids else []
        keep_id = _recommend_keep(songs)
        files = []
        for song in songs:
            files.append({
                "song_id": song.id,
                "file_path": song.file_path,
                "title": song.title,
                "bitrate": song.bitrate,
                "file_size": song.file_size,
                "duration": song.duration,
                "format": song.format,
                "recommended": song.id == keep_id,
            })
        first = members[0]
        result.append({
            "id": first.id,
            "group_hash": gh,
            "similarity": first.similarity,
            "status": first.status,
            "detected_at": first.detected_at,
            "files": files,
        })
    return result, total


def resolve_group(
    db: Session,
    group_hash: str,
    keep_file_id: str,
    action: str,
    recycle_dir: str,
) -> Dict[str, Any]:
    """处理重复组：保留 keep_file_id，对其他文件执行 recycle 或 delete。

    Args:
        db: 数据库会话
        group_hash: 重复组标识
        keep_file_id: 保留的歌曲 id
        action: recycle | delete
        recycle_dir: 回收站目录

    Returns:
        处理结果（kept, removed 列表）
    """
    members = (
        db.query(DuplicateGroup)
        .filter(DuplicateGroup.group_hash == group_hash)
        .all()
    )
    if not members:
        return {"kept": keep_file_id, "removed": [], "error": "重复组不存在"}

    removed: List[Dict[str, Any]] = []
    for member in members:
        if member.song_id == keep_file_id:
            member.status = "resolved"
            continue
        song = db.query(Song).filter(Song.id == member.song_id).first()
        if song is None:
            continue
        path = song.file_path
        if action == "recycle":
            try:
                new_path = move_to_recycle(path, recycle_dir)
                removed.append({"song_id": song.id, "file_path": new_path, "action": "recycled"})
            except Exception as exc:  # noqa: BLE001
                logger.warning("回收失败 %s: %s", path, exc)
                removed.append({"song_id": song.id, "file_path": path, "action": "failed", "error": str(exc)})
        elif action == "delete":
            if delete_file(path):
                removed.append({"song_id": song.id, "file_path": path, "action": "deleted"})
            else:
                removed.append({"song_id": song.id, "file_path": path, "action": "failed"})
        member.status = "resolved"

    db.commit()
    return {"kept": keep_file_id, "removed": removed}
