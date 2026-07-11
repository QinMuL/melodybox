"""Pydantic 请求/响应模型定义。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------- 通用响应 ----------------


class MessageResponse(BaseModel):
    """通用消息响应。"""

    message: str
    success: bool = True


# ---------------- 音乐库 ----------------


class StatsResponse(BaseModel):
    """音乐库统计。"""

    totalSongs: int = 0
    totalArtists: int = 0
    totalAlbums: int = 0
    totalDuplicates: int = 0
    totalSize: int = 0
    formatBreakdown: Dict[str, int] = Field(default_factory=dict)


class ArtistItem(BaseModel):
    id: str
    name: str
    name_normalized: Optional[str] = None
    cover_url: Optional[str] = None
    album_count: int = 0
    song_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlbumItem(BaseModel):
    id: str
    artist_id: str
    title: str
    title_normalized: Optional[str] = None
    year: Optional[int] = None
    cover_url: Optional[str] = None
    song_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SongItem(BaseModel):
    id: str
    album_id: str
    title: str
    track_number: Optional[int] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    file_path: str
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    file_modified: Optional[datetime] = None
    indexed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArtistListResponse(BaseModel):
    """艺术家分页列表。"""

    items: List[ArtistItem]
    total: int
    page: int
    pageSize: int


class AlbumListResponse(BaseModel):
    items: List[AlbumItem]
    total: int


class SongListResponse(BaseModel):
    items: List[SongItem]
    total: int


class SearchResultItem(BaseModel):
    """搜索结果项（type 标识实体类型）。"""

    type: str  # artist | album | song
    id: str
    name: str
    detail: Optional[str] = None


class SearchResponse(BaseModel):
    items: List[SearchResultItem]
    total: int


# ---------------- 整理任务 ----------------


class OrganizeConfig(BaseModel):
    """整理配置。"""

    inputDir: str
    outputDir: str
    recycleDir: str
    namingTemplate: str = "{artist}/{album}/{track:02d}-{title}.{ext}"
    moveInsteadOfCopy: bool = False
    overwritePolicy: str = "skip"  # skip | overwrite | rename
    excludePatterns: List[str] = Field(default_factory=list)


class PreviewRequest(BaseModel):
    """预览整理请求。"""

    inputDir: Optional[str] = None
    outputDir: Optional[str] = None
    namingTemplate: Optional[str] = None
    moveInsteadOfCopy: Optional[bool] = None
    overwritePolicy: Optional[str] = None
    excludePatterns: Optional[List[str]] = None


class PreviewItem(BaseModel):
    """单个文件预览结果。"""

    source: str
    target: str
    action: str  # move | copy | skip
    reason: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    title: Optional[str] = None
    track_number: Optional[int] = None


class PreviewResponse(BaseModel):
    items: List[PreviewItem]
    total: int
    skipped: int


class StartTaskRequest(BaseModel):
    """启动整理任务请求。"""

    config: Optional[OrganizeConfig] = None


class TaskStatusResponse(BaseModel):
    id: str
    task_type: str
    status: str
    progress: float
    total_files: int
    processed_files: int
    current_file: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: List[TaskStatusResponse]
    total: int
    page: int
    pageSize: int


class StartTaskResponse(BaseModel):
    """启动任务响应。"""

    taskId: str
    status: str


# ---------------- 去重 ----------------


class DuplicateGroupItem(BaseModel):
    """重复组中的单首歌曲项。"""

    song_id: str
    file_path: str
    title: str
    bitrate: Optional[int] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    recommended: bool = False  # 是否推荐保留


class DuplicateGroupResponse(BaseModel):
    """重复组详情。"""

    id: str
    group_hash: str
    similarity: float
    status: str
    detected_at: Optional[datetime] = None
    files: List[DuplicateGroupItem] = Field(default_factory=list)


class DuplicateGroupListResponse(BaseModel):
    items: List[DuplicateGroupResponse]
    total: int
    page: int
    pageSize: int


class ResolveDuplicateRequest(BaseModel):
    """处理重复组请求。"""

    keepFileId: str
    action: str = "recycle"  # recycle | delete


# ---------------- 设置 ----------------


class SystemSettings(BaseModel):
    """系统配置。"""

    inputDir: str
    outputDir: str
    recycleDir: str
    dbPath: str
    logLevel: str
    supportedFormats: List[str] = Field(default_factory=list)
    concurrency: int = 4


class TestDirRequest(BaseModel):
    path: str


class TestDirResponse(BaseModel):
    accessible: bool
    writable: bool
    message: str
