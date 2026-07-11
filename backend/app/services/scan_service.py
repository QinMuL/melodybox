"""音乐库扫描服务。

扫描指定目录下的音频文件，读取元数据并写入数据库
（artists、albums、songs 表）。
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models import Album, Artist, Song, normalize_name
from app.services import metadata_service
from app.utils.file_utils import compute_file_hash, file_size, find_audio_files

logger = logging.getLogger(__name__)


def _get_or_create_artist(db: Session, name: str) -> Artist:
    """获取或创建艺术家记录（按标准化名称去重）。"""
    norm = normalize_name(name)
    artist = (
        db.query(Artist)
        .filter(Artist.name_normalized == norm)
        .first()
    )
    if artist is None:
        artist = Artist(
            name=name or "Unknown",
            name_normalized=norm,
        )
        db.add(artist)
        db.flush()
    return artist


def _get_or_create_album(
    db: Session, artist: Artist, title: str, year=None
) -> Album:
    """获取或创建专辑记录（按艺术家 + 标准化标题去重）。"""
    norm = normalize_name(title)
    album = (
        db.query(Album)
        .filter(Album.artist_id == artist.id, Album.title_normalized == norm)
        .first()
    )
    if album is None:
        album = Album(
            artist_id=artist.id,
            title=title or "Unknown",
            title_normalized=norm,
            year=year,
        )
        db.add(album)
        db.flush()
    elif album.year is None and year is not None:
        album.year = year
    return album


def _index_file(
    db: Session, file_path: str, metadata: Dict, compute_hash: bool = False
) -> Song:
    """将单个文件索引到数据库（按 file_path 去重更新）。"""
    artist_name = metadata.get("artist") or "Unknown"
    album_title = metadata.get("album") or "Unknown"
    title = metadata.get("title") or "Unknown"
    track_number = metadata.get("track_number")
    year = metadata.get("year")
    duration = metadata.get("duration")
    fmt = metadata.get("format")
    bitrate = metadata.get("bitrate")
    sample_rate = metadata.get("sample_rate")
    channels = metadata.get("channels")

    artist = _get_or_create_artist(db, artist_name)
    album = _get_or_create_album(db, artist, album_title, year)

    # 已存在则更新
    song = db.query(Song).filter(Song.file_path == file_path).first()
    if song is None:
        song = Song(
            album_id=album.id,
            title=title,
            track_number=track_number,
            duration=duration,
            format=fmt,
            bitrate=bitrate,
            sample_rate=sample_rate,
            channels=channels,
            file_path=file_path,
            file_size=file_size(file_path),
            file_hash=compute_file_hash(file_path) if compute_hash else None,
        )
        db.add(song)
        db.flush()
    else:
        song.album_id = album.id
        song.title = title
        song.track_number = track_number
        song.duration = duration
        song.format = fmt
        song.bitrate = bitrate
        song.sample_rate = sample_rate
        song.channels = channels
        song.file_size = file_size(file_path)
        if song.file_hash is None and compute_hash:
            song.file_hash = compute_file_hash(file_path)
        song.indexed_at = datetime.utcnow()

    # 更新文件修改时间
    try:
        mtime = os.path.getmtime(file_path)
        song.file_modified = datetime.utcfromtimestamp(mtime)
    except OSError:
        pass

    return song


def _recompute_counts(db: Session) -> None:
    """重新统计艺术家与专辑的歌曲数。"""
    # 艺术家歌曲数
    artists = db.query(Artist).all()
    for artist in artists:
        album_ids = [a.id for a in artist.albums]
        song_count = (
            db.query(Song).filter(Song.album_id.in_(album_ids)).count()
            if album_ids
            else 0
        )
        artist.song_count = song_count
        artist.album_count = len(artist.albums)
    # 专辑歌曲数
    albums = db.query(Album).all()
    for album in albums:
        album.song_count = db.query(Song).filter(Song.album_id == album.id).count()


def scan_directory(
    db: Session,
    directory: str,
    exclude_patterns: List[str] | None = None,
    compute_hash: bool = False,
    on_progress=None,
) -> Tuple[int, int]:
    """扫描目录并索引音频文件。

    Args:
        db: 数据库会话
        directory: 扫描目录
        exclude_patterns: 排除模式
        compute_hash: 是否计算文件 MD5
        on_progress: 进度回调 (processed, total, current_file)

    Returns:
        (indexed_count, total_count) 已索引数与总数
    """
    files = find_audio_files(directory, exclude_patterns)
    total = len(files)
    indexed = 0

    for idx, file_path in enumerate(files, start=1):
        try:
            metadata = metadata_service.read_metadata(file_path)
            _index_file(db, file_path, metadata, compute_hash=compute_hash)
            indexed += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("索引文件失败 %s: %s", file_path, exc)
        if on_progress is not None:
            on_progress(idx, total, file_path)

    _recompute_counts(db)
    db.commit()
    return indexed, total


async def run_scan_task(
    task_id: str,
    directory: str,
    exclude_patterns: List[str] | None,
    db_session_factory,
) -> Dict[str, Any]:
    """执行扫描入库的异步任务。

    Args:
        task_id: 任务 ID
        directory: 扫描目录
        exclude_patterns: 排除模式
        db_session_factory: 返回新数据库会话的可调用对象

    Returns:
        任务结果字典
    """
    from app.services.task_manager import task_manager
    from app.models import OrganizeTask, TaskLog

    db = db_session_factory()
    try:
        # 更新任务记录为 running
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "running"
            task.task_type = "scan"
            task.started_at = datetime.utcnow()
            db.commit()

        await task_manager.send_log(task_id, "info", f"开始扫描目录: {directory}")

        # 进度回调（同步 → 推送到 WebSocket）
        loop = asyncio.get_event_loop()

        def _on_progress(processed: int, total: int, current_file: str) -> None:
            progress = (processed / total * 100) if total else 100.0
            # 推送到 WebSocket（线程安全：通过 run_coroutine_threadsafe）
            import asyncio as _asyncio
            fut = _asyncio.run_coroutine_threadsafe(
                task_manager.update_progress(
                    task_id,
                    progress=progress,
                    total_files=total,
                    processed_files=processed,
                    current_file=current_file,
                ),
                loop,
            )
            try:
                fut.result(timeout=1)
            except Exception:
                pass
            # 同步更新数据库
            if task is not None:
                task.processed_files = processed
                task.total_files = total
                task.progress = progress
                task.current_file = current_file
                db.commit()

        # 在线程池中执行同步扫描
        indexed, total = await loop.run_in_executor(
            None,
            lambda: scan_directory(db, directory, exclude_patterns, on_progress=_on_progress),
        )

        result = {"indexed": indexed, "total": total, "directory": directory}
        if task is not None:
            task.status = "completed"
            task.progress = 100.0
            task.processed_files = total
            task.total_files = total
            task.current_file = None
            task.completed_at = datetime.utcnow()
            task.result = result
            db.commit()
        await task_manager.send_log(
            task_id, "info",
            f"扫描完成：共 {total} 个文件，成功入库 {indexed} 个",
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("扫描任务异常: %s", task_id)
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.result = {"error": str(exc)}
            db.commit()
        db.add(TaskLog(task_id=task_id, level="error", message=f"扫描异常: {exc}"))
        db.commit()
        raise
    finally:
        db.close()
