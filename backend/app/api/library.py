"""音乐库查询路由 /api/library。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import load_organize_config
from app.database import SessionLocal, get_db
from app.models import Album, Artist, DuplicateGroup, OrganizeTask, Song, SongArtist
from app.schemas import (
    AlbumListResponse,
    ArtistItem,
    ArtistListResponse,
    SearchResponse,
    SearchResultItem,
    SongListResponse,
    StartTaskResponse,
    StatsResponse,
    TaskStatusResponse,
)
from app.services.scan_service import run_scan_task
from app.services.task_manager import task_manager

router = APIRouter(prefix="/library", tags=["library"])


class ScanRequest(BaseModel):
    """扫描入库请求。"""
    directory: Optional[str] = None
    excludePatterns: Optional[List[str]] = None
    computeHash: bool = False


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    """获取音乐库统计信息。"""
    total_songs = db.query(func.count(Song.id)).scalar() or 0
    total_artists = db.query(func.count(Artist.id)).scalar() or 0
    total_albums = db.query(func.count(Album.id)).scalar() or 0
    total_duplicates = db.query(
        func.count(func.distinct(DuplicateGroup.group_hash))
    ).scalar() or 0
    total_size = db.query(func.coalesce(func.sum(Song.file_size), 0)).scalar() or 0

    # 格式分布
    format_rows = (
        db.query(Song.format, func.count(Song.id))
        .group_by(Song.format)
        .all()
    )
    format_breakdown = [
        {"format": fmt or "unknown", "count": count}
        for fmt, count in format_rows
    ]

    return StatsResponse(
        total_songs=total_songs,
        total_artists=total_artists,
        total_albums=total_albums,
        total_duplicates=total_duplicates,
        total_size=int(total_size),
        format_breakdown=format_breakdown,
    )


@router.get("/artists", response_model=ArtistListResponse)
def list_artists(
    sortBy: str = Query("name", description="排序字段：name | song_count | album_count"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ArtistListResponse:
    """获取艺术家分页列表。"""
    query = db.query(Artist)

    # 排序
    if sortBy == "song_count":
        query = query.order_by(Artist.song_count.desc(), Artist.name_normalized.asc())
    elif sortBy == "album_count":
        query = query.order_by(Artist.album_count.desc(), Artist.name_normalized.asc())
    else:
        query = query.order_by(Artist.name_normalized.asc())

    total = query.count()
    items = query.offset((page - 1) * pageSize).limit(pageSize).all()
    return ArtistListResponse(
        items=[ArtistItem.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=pageSize,
    )


@router.get("/artists/{artist_id}/albums", response_model=AlbumListResponse)
def list_artist_albums(
    artist_id: str,
    db: Session = Depends(get_db),
) -> AlbumListResponse:
    """获取指定艺术家的专辑列表。

    基于多对多关联：返回该艺人参与的所有歌曲所在的专辑（去重），
    因此合作艺人也能看到他/她参与的合作专辑。
    """
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="艺术家不存在")

    # 通过 song_artists 找该艺人参与的所有歌曲 id
    song_ids_subq = (
        db.query(SongArtist.song_id)
        .filter(SongArtist.artist_id == artist_id)
        .subquery()
    )
    # 这些歌曲所在的不同专辑 id
    album_ids_subq = (
        db.query(Song.album_id)
        .filter(Song.id.in_(song_ids_subq))
        .distinct()
        .subquery()
    )
    albums = (
        db.query(Album)
        .filter(Album.id.in_(album_ids_subq))
        .order_by(Album.year.asc().nullslast(), Album.title_normalized.asc())
        .all()
    )
    from app.schemas import AlbumItem
    return AlbumListResponse(
        items=[AlbumItem.model_validate(a) for a in albums],
        total=len(albums),
    )


@router.get("/albums/{album_id}/songs", response_model=SongListResponse)
def list_album_songs(
    album_id: str,
    db: Session = Depends(get_db),
) -> SongListResponse:
    """获取指定专辑的歌曲列表。"""
    album = db.query(Album).filter(Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="专辑不存在")
    songs = (
        db.query(Song)
        .filter(Song.album_id == album_id)
        .order_by(Song.track_number.asc().nullslast(), Song.title.asc())
        .all()
    )
    from app.schemas import SongItem
    return SongListResponse(
        items=[SongItem.model_validate(s) for s in songs],
        total=len(songs),
    )


@router.get("/albums", response_model=AlbumListResponse)
def list_albums(
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> AlbumListResponse:
    """获取所有专辑分页列表。"""
    query = db.query(Album).order_by(Album.title_normalized.asc())
    total = query.count()
    albums = query.offset((page - 1) * pageSize).limit(pageSize).all()
    from app.schemas import AlbumItem
    return AlbumListResponse(
        items=[AlbumItem.model_validate(a) for a in albums],
        total=total,
    )


@router.get("/songs", response_model=SongListResponse)
def list_songs(
    page: int = Query(1, ge=1),
    pageSize: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> SongListResponse:
    """获取所有歌曲分页列表。"""
    query = db.query(Song).order_by(Song.title.asc())
    total = query.count()
    songs = query.offset((page - 1) * pageSize).limit(pageSize).all()
    from app.schemas import SongItem
    return SongListResponse(
        items=[SongItem.model_validate(s) for s in songs],
        total=total,
    )


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    type: str = Query("all", description="搜索类型：all | artist | album | song"),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """全局搜索艺术家、专辑、歌曲。"""
    keyword = f"%{q}%"
    items: List[SearchResultItem] = []

    if type in ("all", "artist"):
        artists = (
            db.query(Artist)
            .filter(
                or_(
                    Artist.name.ilike(keyword),
                    Artist.name_normalized.ilike(keyword),
                )
            )
            .order_by(Artist.name_normalized.asc())
            .limit(50)
            .all()
        )
        for a in artists:
            items.append(SearchResultItem(
                type="artist", id=a.id, name=a.name,
                detail=f"{a.album_count} 张专辑 · {a.song_count} 首",
            ))

    if type in ("all", "album"):
        albums = (
            db.query(Album)
            .filter(
                or_(
                    Album.title.ilike(keyword),
                    Album.title_normalized.ilike(keyword),
                )
            )
            .order_by(Album.title_normalized.asc())
            .limit(50)
            .all()
        )
        for al in albums:
            artist_name = al.artist.name if al.artist else "Unknown"
            items.append(SearchResultItem(
                type="album", id=al.id, name=al.title,
                detail=f"{artist_name}" + (f" · {al.year}" if al.year else ""),
            ))

    if type in ("all", "song"):
        songs = (
            db.query(Song)
            .filter(Song.title.ilike(keyword))
            .order_by(Song.title.asc())
            .limit(50)
            .all()
        )
        for s in songs:
            artist_name = s.album.artist.name if s.album and s.album.artist else "Unknown"
            album_title = s.album.title if s.album else "Unknown"
            items.append(SearchResultItem(
                type="song", id=s.id, name=s.title,
                detail=f"{artist_name} · {album_title}",
            ))

    return SearchResponse(items=items, total=len(items))


@router.post("/scan", response_model=StartTaskResponse)
def scan_library(
    req: ScanRequest,
    db: Session = Depends(get_db),
) -> StartTaskResponse:
    """启动扫描入库任务。

    扫描指定目录下所有音频文件，读取元数据并写入数据库。
    不指定 directory 时使用已保存的整理配置中的 inputDir。
    """
    # 确定扫描目录
    saved = load_organize_config()
    directory = req.directory or saved.get("inputDir") or "/music"
    exclude_patterns = req.excludePatterns if req.excludePatterns is not None else saved.get("excludePatterns", [])

    # 创建任务记录
    task = OrganizeTask(
        task_type="scan",
        status="pending",
        progress=0.0,
        total_files=0,
        processed_files=0,
        config={
            "directory": directory,
            "excludePatterns": exclude_patterns,
            "computeHash": req.computeHash,
        },
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 启动后台扫描任务
    task_manager.start_task(
        task.id,
        run_scan_task(task.id, directory, exclude_patterns, SessionLocal),
    )
    return StartTaskResponse(taskId=task.id, status=task.status)


@router.get("/scan/status", response_model=TaskStatusResponse)
def get_scan_status(
    taskId: Optional[str] = Query(None, description="任务ID；不传则返回最新一次扫描任务"),
    db: Session = Depends(get_db),
) -> TaskStatusResponse:
    """查询扫描任务状态。

    - 传 taskId：返回指定任务
    - 不传：返回最新一次扫描任务
    """
    query = db.query(OrganizeTask).filter(OrganizeTask.task_type == "scan")
    if taskId:
        query = query.filter(OrganizeTask.id == taskId)
    task = query.order_by(OrganizeTask.created_at.desc()).first()
    if task is None:
        raise HTTPException(status_code=404, detail="尚无扫描任务")
    return TaskStatusResponse.model_validate(task)


def _find_cover_file(album_id: str) -> Optional[Path]:
    """查找专辑封面文件。"""
    from app.config import DATA_DIR

    covers_dir = DATA_DIR / "covers"
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        p = covers_dir / f"{album_id}{ext}"
        if p.exists():
            return p
    return None


def _find_artist_avatar_file(artist_id: str) -> Optional[Path]:
    """查找艺术家头像文件（MusicBrainz/Wikipedia 获取的真实头像）。"""
    from app.config import DATA_DIR

    avatars_dir = DATA_DIR / "covers" / "artists"
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        p = avatars_dir / f"{artist_id}{ext}"
        if p.exists():
            return p
    return None


@router.get("/albums/{album_id}/cover")
def get_album_cover(album_id: str, db: Session = Depends(get_db)):
    """返回专辑封面图片。"""
    album = db.query(Album).filter(Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="专辑不存在")
    cover = _find_cover_file(album_id)
    if cover is None:
        raise HTTPException(status_code=404, detail="无封面图")
    media_type = "image/png" if cover.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(str(cover), media_type=media_type)


@router.get("/artists/{artist_id}/avatar")
def get_artist_avatar(artist_id: str, db: Session = Depends(get_db)):
    """返回艺术家头像。优先返回真实头像，无则生成首字母 SVG。"""
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="艺术家不存在")

    # 优先返回真实头像
    avatar = _find_artist_avatar_file(artist_id)
    if avatar is not None:
        media_type = "image/png" if avatar.suffix.lower() == ".png" else "image/jpeg"
        return FileResponse(str(avatar), media_type=media_type)

    # 回退：生成首字母 SVG
    name = artist.name or "U"
    initial = name[0].upper() if name else "U"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#31C27C"/>
      <stop offset="100%" stop-color="#1A9B5F"/>
    </linearGradient>
  </defs>
  <rect width="200" height="200" fill="url(#bg)"/>
  <text x="100" y="100" font-size="100" font-family="sans-serif" fill="white" text-anchor="middle" dominant-baseline="central" font-weight="bold">{initial}</text>
</svg>'''
    return Response(content=svg, media_type="image/svg+xml")


@router.post("/artists/{artist_id}/fetch-avatar")
def fetch_artist_avatar(artist_id: str, db: Session = Depends(get_db)):
    """手动触发获取艺术家头像（MusicBrainz + Wikipedia）。"""
    from app.services.artist_image_service import save_artist_avatar

    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="艺术家不存在")

    success = save_artist_avatar(artist_id, artist.name)
    return {"success": success, "artist": artist.name}
