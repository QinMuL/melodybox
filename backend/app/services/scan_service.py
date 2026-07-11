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

from app.models import Album, Artist, Song, SongArtist, normalize_name
from app.services import metadata_service
from app.utils.file_utils import compute_file_hash, file_size, find_audio_files

logger = logging.getLogger(__name__)


# 多艺人分隔符：& / 、 / , / feat. / ft. / and
_ARTIST_SEPARATORS = [" & ", "、", " / ", "/", ", ", ",", " feat. ", " ft. ", " and ", " feat ", " ft "]


def split_artist_names(artist_str: str) -> List[str]:
    """将多艺人字符串拆分为独立艺人名列表。

    例如 "冒海飞 & 徐丽东" → ["冒海飞", "徐丽东"]
         "杨丞琳、欧阳娜娜" → ["杨丞琳", "欧阳娜娜"]
    """
    if not artist_str:
        return ["Unknown"]
    text = artist_str.strip()
    # 依次按各分隔符拆分
    parts = [text]
    for sep in _ARTIST_SEPARATORS:
        new_parts = []
        for p in parts:
            new_parts.extend(p.split(sep))
        parts = new_parts
    # 清理空白、去重保序
    seen = set()
    result = []
    for p in parts:
        name = p.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result if result else ["Unknown"]


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


def _extract_album_cover(album_id: str, file_path: str) -> None:
    """为专辑提取封面图（已存在则跳过）。"""
    from app.config import DATA_DIR

    covers_dir = DATA_DIR / "covers"
    # 检查是否已有封面（任意扩展名）
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        if (covers_dir / f"{album_id}{ext}").exists():
            return
    # 提取嵌入式封面
    result = metadata_service.extract_cover(file_path)
    if result is None:
        return
    data, mime = result
    covers_dir.mkdir(parents=True, exist_ok=True)
    ext = ".png" if "png" in mime else ".jpg"
    cover_file = covers_dir / f"{album_id}{ext}"
    try:
        with open(cover_file, "wb") as f:
            f.write(data)
        logger.info("提取封面: 专辑 %d ← %s", album_id, file_path)
    except OSError as exc:
        logger.warning("保存封面失败: %s", exc)


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

    # 多艺人拆分：每个独立艺人都创建 Artist 记录，专辑归第一艺人
    artist_names = split_artist_names(artist_name)
    primary_artist = _get_or_create_artist(db, artist_names[0])
    # 其余合作艺人也创建 Artist 记录（艺术家列表会显示）
    for name in artist_names[1:]:
        _get_or_create_artist(db, name)
    album = _get_or_create_album(db, primary_artist, album_title, year)

    # 提取专辑封面图（每张专辑只提取一次）
    _extract_album_cover(album.id, file_path)

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
        song.indexed_at = datetime.now()

    # 同步 SongArtist 关联：先删旧关联再按当前艺人列表重建
    db.query(SongArtist).filter(SongArtist.song_id == song.id).delete()
    for idx, name in enumerate(artist_names):
        a = _get_or_create_artist(db, name)
        role = "primary" if idx == 0 else "featured"
        db.add(SongArtist(song_id=song.id, artist_id=a.id, role=role))

    # 更新文件修改时间
    try:
        mtime = os.path.getmtime(file_path)
        song.file_modified = datetime.fromtimestamp(mtime)
    except OSError:
        pass

    return song


def _recompute_counts(db: Session) -> None:
    """重新统计艺术家与专辑的歌曲数。

    艺术家歌曲数 / 专辑数基于 song_artists 多对多关联统计：
    - song_count = 该艺人参与的歌曲总数（含合作）
    - album_count = 该艺人参与的歌曲所在的不同专辑数
    """
    artists = db.query(Artist).all()
    for artist in artists:
        # 该艺人参与的歌曲 id
        song_ids = [
            row.song_id
            for row in db.query(SongArtist).filter(SongArtist.artist_id == artist.id).all()
        ]
        if song_ids:
            artist.song_count = len(song_ids)
            # 这些歌曲所在的不同专辑数
            album_count = (
                db.query(Song.album_id)
                .filter(Song.id.in_(song_ids))
                .distinct()
                .count()
            )
            artist.album_count = album_count
        else:
            artist.song_count = 0
            artist.album_count = 0
    # 专辑歌曲数（按专辑实际包含的歌曲数）
    albums = db.query(Album).all()
    for album in albums:
        album.song_count = db.query(Song).filter(Song.album_id == album.id).count()


def _cleanup_orphans(db: Session, current_files: set) -> int:
    """删除数据库中已不存在的文件记录（孤儿歌曲）。

    同时删除该歌曲的 SongArtist 关联。空专辑也一并清理。
    """
    orphans = (
        db.query(Song)
        .filter(~Song.file_path.in_(current_files))
        .all()
    )
    if not orphans:
        return 0
    orphan_ids = [s.id for s in orphans]
    # 删 SongArtist 关联
    db.query(SongArtist).filter(SongArtist.song_id.in_(orphan_ids)).delete(
        synchronize_session=False
    )
    # 删 Song
    db.query(Song).filter(Song.id.in_(orphan_ids)).delete(
        synchronize_session=False
    )
    # 删空专辑（没有任何歌曲的专辑）
    used_album_ids = db.query(Song.album_id).distinct().subquery()
    db.query(Album).filter(~Album.id.in_(used_album_ids)).delete(
        synchronize_session=False
    )
    logger.info("清理孤儿记录 %d 条", len(orphans))
    return len(orphans)


def scan_directory(
    db: Session,
    directory: str,
    exclude_patterns: List[str] | None = None,
    compute_hash: bool = False,
    on_progress=None,
) -> Tuple[int, int, int]:
    """扫描目录并索引音频文件（增量：跳过未修改文件）。

    Args:
        db: 数据库会话
        directory: 扫描目录
        exclude_patterns: 排除模式
        compute_hash: 是否计算文件 MD5
        on_progress: 进度回调 (processed, total, current_file)

    Returns:
        (indexed, total, skipped) 新入库数、总文件数、跳过数
    """
    from concurrent.futures import ThreadPoolExecutor

    logger.info("开始扫描目录: %s (计算哈希: %s)", directory, compute_hash)
    files = find_audio_files(directory, exclude_patterns)
    total = len(files)
    logger.info("发现 %d 个音频文件", total)

    if total == 0:
        cleaned = _cleanup_orphans(db, set())
        _recompute_counts(db)
        db.commit()
        logger.info("扫描完成：0 个文件，清理孤儿 %d 条", cleaned)
        return 0, 0, 0

    # 查询数据库已有文件 → {file_path: file_modified}
    existing = {
        s.file_path: s.file_modified
        for s in db.query(Song.file_path, Song.file_modified).all()
    }

    # 增量分组：未修改的跳过，其余扫描
    files_to_scan: List[str] = []
    skipped = 0
    for fp in files:
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fp))
        except OSError:
            mtime = None
        if (
            fp in existing
            and existing[fp] is not None
            and mtime is not None
            and existing[fp] == mtime
        ):
            skipped += 1
        else:
            files_to_scan.append(fp)
    logger.info("跳过 %d 个未修改文件，待扫描 %d 个", skipped, len(files_to_scan))

    # 并发读取元数据（mutagen 是同步 IO，多线程加速）
    indexed = 0
    if files_to_scan:
        with ThreadPoolExecutor(max_workers=8) as executor:
            metadata_iter = executor.map(
                metadata_service.read_metadata, files_to_scan
            )
            for fp, metadata in zip(files_to_scan, metadata_iter):
                try:
                    _index_file(db, fp, metadata, compute_hash=compute_hash)
                    indexed += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("索引文件失败 %s: %s", fp, exc)
                if on_progress is not None:
                    # 进度 = 跳过数 + 当前已处理
                    on_progress(skipped + indexed, total, fp)
    else:
        if on_progress is not None:
            on_progress(total, total, "")

    # 清理孤儿（文件系统中已不存在的数据库记录）
    _cleanup_orphans(db, set(files))

    _recompute_counts(db)
    db.commit()
    logger.info(
        "扫描完成：共 %d 个文件，新入库 %d 个，跳过 %d 个",
        total, indexed, skipped,
    )
    return indexed, total, skipped


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
            task.started_at = datetime.now()
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
        indexed, total, skipped = await loop.run_in_executor(
            None,
            lambda: scan_directory(db, directory, exclude_patterns, on_progress=_on_progress),
        )

        result = {
            "indexed": indexed,
            "total": total,
            "skipped": skipped,
            "directory": directory,
        }
        if task is not None:
            task.status = "completed"
            task.progress = 100.0
            task.processed_files = total
            task.total_files = total
            task.current_file = None
            task.completed_at = datetime.now()
            task.result = result
            db.commit()
        await task_manager.send_log(
            task_id, "info",
            f"扫描完成：共 {total} 个文件，新入库 {indexed} 个，跳过未修改 {skipped} 个",
        )

        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("扫描任务异常: %s", task_id)
        task = db.query(OrganizeTask).filter(OrganizeTask.id == task_id).first()
        if task is not None:
            task.status = "failed"
            task.completed_at = datetime.now()
            task.result = {"error": str(exc)}
            db.commit()
        db.add(TaskLog(task_id=task_id, level="error", message=f"扫描异常: {exc}"))
        db.commit()
        raise
    finally:
        db.close()
