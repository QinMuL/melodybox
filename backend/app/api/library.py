"""音乐库查询路由 /api/library。"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Album, Artist, DuplicateGroup, Song
from app.schemas import (
    AlbumListResponse,
    ArtistItem,
    ArtistListResponse,
    SearchResponse,
    SearchResultItem,
    SongListResponse,
    StatsResponse,
)

router = APIRouter(prefix="/library", tags=["library"])


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
    format_breakdown = {
        (fmt or "unknown"): count for fmt, count in format_rows
    }

    return StatsResponse(
        totalSongs=total_songs,
        totalArtists=total_artists,
        totalAlbums=total_albums,
        totalDuplicates=total_duplicates,
        totalSize=int(total_size),
        formatBreakdown=format_breakdown,
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
        pageSize=pageSize,
    )


@router.get("/artists/{artist_id}/albums", response_model=AlbumListResponse)
def list_artist_albums(
    artist_id: str,
    db: Session = Depends(get_db),
) -> AlbumListResponse:
    """获取指定艺术家的专辑列表。"""
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="艺术家不存在")
    albums = (
        db.query(Album)
        .filter(Album.artist_id == artist_id)
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
