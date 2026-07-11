"""SQLAlchemy 数据模型定义。

所有表的主键 id 均使用 uuid4().hex 生成的字符串。
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id() -> str:
    """生成 UUID 字符串主键。"""
    return uuid4().hex


def normalize_name(name: str) -> str:
    """将名称标准化：去除首尾空白、转小写、折叠空白、去除标点。

    用于艺术家/专辑名的唯一性比较与检索排序。
    """
    if not name:
        return ""
    # NFKC 规范化以兼容全角/半角
    text = unicodedata.normalize("NFKC", str(name))
    text = text.strip().lower()
    # 移除常见标点与符号
    text = re.sub(r"[\s\W_]+", " ", text, flags=re.UNICODE)
    return text.strip()


class Artist(Base):
    """艺术家表。"""

    __tablename__ = "artists"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, default="Unknown")
    name_normalized = Column(String, index=True, default="")
    cover_url = Column(String, nullable=True)
    album_count = Column(Integer, default=0, nullable=False)
    song_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    albums = relationship("Album", back_populates="artist", cascade="all, delete-orphan")


class Album(Base):
    """专辑表。"""

    __tablename__ = "albums"

    id = Column(String, primary_key=True, default=gen_id)
    artist_id = Column(String, ForeignKey("artists.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="Unknown")
    title_normalized = Column(String, index=True, default="")
    year = Column(Integer, nullable=True)
    cover_url = Column(String, nullable=True)
    song_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    artist = relationship("Artist", back_populates="albums")
    songs = relationship("Song", back_populates="album", cascade="all, delete-orphan")


class Song(Base):
    """歌曲表。"""

    __tablename__ = "songs"

    id = Column(String, primary_key=True, default=gen_id)
    album_id = Column(String, ForeignKey("albums.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="Unknown")
    track_number = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)  # 秒
    format = Column(String, nullable=True)  # mp3, flac ...
    bitrate = Column(Integer, nullable=True)  # kbps
    sample_rate = Column(Integer, nullable=True)  # Hz
    channels = Column(Integer, nullable=True)
    file_path = Column(String, unique=True, nullable=False)
    file_size = Column(Integer, nullable=True)  # 字节
    file_hash = Column(String, nullable=True, index=True)  # MD5
    acoustic_fingerprint = Column(String, nullable=True)
    file_modified = Column(DateTime, nullable=True)
    indexed_at = Column(DateTime, default=datetime.now, nullable=False)

    album = relationship("Album", back_populates="songs")


class SongArtist(Base):
    """歌曲-艺术家多对多关联表。

    一首歌可有多个艺术家（合作曲目），role 区分主艺人 / 合作艺人。
    """

    __tablename__ = "song_artists"

    id = Column(String, primary_key=True, default=gen_id)
    song_id = Column(String, ForeignKey("songs.id"), nullable=False, index=True)
    artist_id = Column(String, ForeignKey("artists.id"), nullable=False, index=True)
    role = Column(String, default="primary", nullable=False)  # primary | featured
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class DuplicateGroup(Base):
    """重复组表：记录每首歌曲所属的重复组及处理状态。"""

    __tablename__ = "duplicate_groups"

    id = Column(String, primary_key=True, default=gen_id)
    song_id = Column(String, ForeignKey("songs.id"), nullable=False, index=True)
    group_hash = Column(String, nullable=False, index=True)  # 组标识（hash 或模糊键）
    similarity = Column(Float, default=100.0, nullable=False)  # 0-100
    status = Column(String, default="pending", nullable=False)  # pending | resolved
    detected_at = Column(DateTime, default=datetime.now, nullable=False)


class OrganizeTask(Base):
    """整理任务表。"""

    __tablename__ = "organize_tasks"

    id = Column(String, primary_key=True, default=gen_id)
    task_type = Column(String, nullable=False, default="organize")  # organize | scan_duplicates
    status = Column(String, default="pending", nullable=False)  # pending|running|completed|failed
    progress = Column(Float, default=0.0, nullable=False)  # 0-100
    total_files = Column(Integer, default=0, nullable=False)
    processed_files = Column(Integer, default=0, nullable=False)
    current_file = Column(String, nullable=True)
    config = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    logs = relationship(
        "TaskLog", back_populates="task", cascade="all, delete-orphan"
    )


class TaskLog(Base):
    """任务日志表。"""

    __tablename__ = "task_logs"

    id = Column(String, primary_key=True, default=gen_id)
    task_id = Column(String, ForeignKey("organize_tasks.id"), nullable=False, index=True)
    level = Column(String, default="info", nullable=False)  # info|warning|error
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    task = relationship("OrganizeTask", back_populates="logs")
