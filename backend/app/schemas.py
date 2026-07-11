"""Pydantic 请求/响应模型定义。

所有模型继承 CamelModel，字段名使用 snake_case（与 ORM 模型一致），
通过 alias_generator 自动生成 camelCase alias，JSON 输出时使用 alias。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """基类：自动生成 camelCase alias，支持从 ORM 属性读取。"""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


# ---------------- 通用响应 ----------------


class MessageResponse(CamelModel):
    """通用消息响应。"""

    message: str
    success: bool = True


# ---------------- 音乐库 ----------------


class FormatCount(CamelModel):
    """格式分布项。"""
    format: str
    count: int


class StatsResponse(CamelModel):
    """音乐库统计。"""

    total_songs: int = 0
    total_artists: int = 0
    total_albums: int = 0
    total_duplicates: int = 0
    total_size: int = 0
    format_breakdown: List[FormatCount] = Field(default_factory=list)


class ArtistItem(CamelModel):
    id: str
    name: str
    name_normalized: Optional[str] = None
    cover_url: Optional[str] = None
    album_count: int = 0
    song_count: int = 0
    created_at: Optional[datetime] = None


class AlbumItem(CamelModel):
    id: str
    artist_id: str
    title: str
    title_normalized: Optional[str] = None
    year: Optional[int] = None
    cover_url: Optional[str] = None
    song_count: int = 0
    created_at: Optional[datetime] = None


class SongItem(CamelModel):
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


class ArtistListResponse(CamelModel):
    """艺术家分页列表。"""

    items: List[ArtistItem]
    total: int
    page: int = 1
    page_size: int = 50


class AlbumListResponse(CamelModel):
    items: List[AlbumItem]
    total: int


class SongListResponse(CamelModel):
    items: List[SongItem]
    total: int


class SearchResultItem(CamelModel):
    """搜索结果项（type 标识实体类型）。"""

    type: str  # artist | album | song
    id: str
    name: str
    detail: Optional[str] = None


class SearchResponse(CamelModel):
    items: List[SearchResultItem]
    total: int


# ---------------- 整理任务 ----------------


class OrganizeConfig(CamelModel):
    """整理配置。"""

    input_dir: str
    output_dir: str
    recycle_dir: str
    naming_template: str = "{artist}/{album}/{track:02d}-{title}.{ext}"
    move_instead_of_copy: bool = True
    overwrite_policy: str = "skip"  # skip | overwrite | rename
    exclude_patterns: List[str] = Field(default_factory=list)


class PreviewRequest(CamelModel):
    """预览整理请求。"""

    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    mode: str = "organize"  # "rename"（只重命名）或 "organize"（只归类移动）
    naming_template: Optional[str] = None
    move_instead_of_copy: Optional[bool] = None
    overwrite_policy: Optional[str] = None
    exclude_patterns: Optional[List[str]] = None


class PreviewItem(CamelModel):
    """单个文件预览结果。"""

    old_path: str
    new_path: str
    action: str  # move | copy | skip
    reason: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    title: Optional[str] = None
    track_number: Optional[int] = None


class PreviewResponse(CamelModel):
    changes: List[PreviewItem]
    total_changes: int
    skipped: int


class StartTaskRequest(CamelModel):
    """启动整理任务请求。"""

    config: Optional[OrganizeConfig] = None
    mode: str = "organize"  # "rename"（只重命名）或 "organize"（只归类移动）


class TaskStatusResponse(CamelModel):
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


class TaskListResponse(CamelModel):
    items: List[TaskStatusResponse]
    total: int
    page: int = 1
    page_size: int = 10


class StartTaskResponse(CamelModel):
    """启动任务响应。"""

    task_id: str
    status: str


# ---------------- 去重 ----------------


class DuplicateGroupItem(CamelModel):
    """重复组中的单首歌曲项。"""

    song_id: str
    file_path: str
    title: str
    bitrate: Optional[int] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    recommended: bool = False  # 是否推荐保留


class DuplicateGroupResponse(CamelModel):
    """重复组详情。"""

    id: str
    group_hash: str
    similarity: float
    status: str
    detected_at: Optional[datetime] = None
    files: List[DuplicateGroupItem] = Field(default_factory=list)


class DuplicateGroupListResponse(CamelModel):
    items: List[DuplicateGroupResponse]
    total: int
    page: int = 1
    page_size: int = 20


class ResolveDuplicateRequest(CamelModel):
    """处理重复组请求。"""

    keep_file_id: str
    action: str = "recycle"  # recycle | delete


# ---------------- 设置 ----------------


class SystemSettings(CamelModel):
    """系统配置。"""

    input_dir: str
    output_dir: str
    recycle_dir: str
    db_path: str
    log_level: str
    supported_formats: List[str] = Field(default_factory=list)
    concurrency: int = 4


class TestDirRequest(CamelModel):
    path: str


class TestDirResponse(CamelModel):
    accessible: bool
    writable: bool
    message: str
    file_count: int = 0
