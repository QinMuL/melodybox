"""系统日志路由 /api/logs。

读取 /app/data/logs/melodybox.log（及其轮转副本），
支持按级别、关键词筛选，按行数限制返回最新条目。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import DATA_DIR

router = APIRouter(prefix="/logs", tags=["logs"])

# 日志目录与主日志文件
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "melodybox.log"

# 日志行正则：解析 "2026-07-11 12:34:56,789 [LEVEL] name: message"
_LOG_PATTERN = re.compile(
    r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\s+"
    r"\[(?P<level>[A-Z]+)\]\s+"
    r"(?P<name>[^:]+):\s+(?P<msg>.*)$"
)

# 级别权重，用于 >= 筛选
_LEVEL_ORDER = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


class LogEntry(BaseModel):
    """单条日志条目。"""
    time: str
    level: str
    logger: str
    message: str
    raw: str  # 原始行（解析失败时仍可展示）


class LogListResponse(BaseModel):
    """日志列表响应。"""
    total: int  # 返回的条目数
    file: str  # 当前读取的日志文件
    fileSize: int  # 文件大小（字节）
    entries: List[LogEntry]


def _parse_line(line: str) -> LogEntry:
    """解析单行日志，失败时回退为 raw 展示。"""
    m = _LOG_PATTERN.match(line)
    if m:
        return LogEntry(
            time=m.group("time"),
            level=m.group("level"),
            logger=m.group("name").strip(),
            message=m.group("msg"),
            raw=line,
        )
    return LogEntry(time="", level="INFO", logger="", message=line, raw=line)


def _read_log_tail(file_path: Path, max_lines: int = 1000) -> List[str]:
    """从后向前读取日志文件的最后 N 行（避免大文件 OOM）。"""
    if not file_path.exists():
        return []
    lines: List[str] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            # 简单做法：读取全部并切尾，日志已轮转控制大小（10MB）
            all_lines = f.readlines()
            lines = all_lines[-max_lines:]
    except OSError:
        return []
    return lines


@router.get("/", response_model=LogListResponse)
def get_logs(
    level: Optional[str] = Query(None, description="最低日志级别筛选: DEBUG/INFO/WARNING/ERROR/CRITICAL"),
    search: Optional[str] = Query(None, description="关键词搜索（不区分大小写）"),
    limit: int = Query(500, ge=1, le=5000, description="返回最近 N 条"),
) -> LogListResponse:
    """获取系统日志（最新在前）。

    读取 /app/data/logs/melodybox.log 的最后 N 条，按级别和关键词筛选。
    """
    if not LOG_FILE.exists():
        return LogListResponse(total=0, file=str(LOG_FILE), fileSize=0, entries=[])

    file_size = LOG_FILE.stat().st_size
    raw_lines = _read_log_tail(LOG_FILE, max_lines=limit * 5)  # 多读一些以备筛选

    # 解析行
    entries = [_parse_line(line.rstrip("\n")) for line in raw_lines]

    # 级别筛选（>= 指定级别）
    if level:
        lvl = level.upper()
        threshold = _LEVEL_ORDER.get(lvl)
        if threshold is None:
            raise HTTPException(
                status_code=400, detail=f"无效的日志级别: {level}"
            )
        entries = [e for e in entries if _LEVEL_ORDER.get(e.level, 0) >= threshold]

    # 关键词筛选
    if search:
        kw = search.lower()
        entries = [
            e for e in entries
            if kw in e.message.lower() or kw in e.logger.lower() or kw in e.raw.lower()
        ]

    # 截取最后 limit 条并反转（最新在前）
    entries = entries[-limit:]
    entries.reverse()

    return LogListResponse(
        total=len(entries),
        file=str(LOG_FILE),
        fileSize=file_size,
        entries=entries,
    )


@router.get("/files", response_model=List[str])
def list_log_files() -> List[str]:
    """列出所有日志文件（含轮转副本 .1 .2 ...）。"""
    if not LOG_DIR.exists():
        return []
    files = sorted(
        LOG_DIR.glob("melodybox.log*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [f.name for f in files]


@router.delete("/", response_model=dict)
def clear_logs() -> dict:
    """清空当前主日志文件内容（轮转副本保留）。"""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.truncate(0)
            return {"status": "ok", "message": "日志已清空"}
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"清空日志失败: {exc}")
    return {"status": "ok", "message": "日志文件不存在"}
