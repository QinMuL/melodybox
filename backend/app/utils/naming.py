"""文件名模板渲染与文件名清理工具。"""
from __future__ import annotations

import re
from typing import Any, Dict


# 文件系统非法字符（Windows 与 Linux 通用）
_ILLEGAL_CHARS_PATTERN = re.compile(r'[\\/:*?"<>|]')
# 控制字符
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x1f]")
# 保留文件名（Windows）
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}
# 每段文件名最大长度（留出后缀空间）
_MAX_NAME_LENGTH = 200


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符。

    - 替换非法字符 / \\ : * ? " < > | 为下划线
    - 移除控制字符
    - 去除首尾空格与点（Windows 不允许首尾空格或点）
    - 处理保留文件名（如 CON）
    - 限制长度
    """
    if name is None:
        return "Unknown"
    text = str(name)
    # 替换非法字符
    text = _ILLEGAL_CHARS_PATTERN.sub("_", text)
    # 移除控制字符
    text = _CONTROL_CHARS_PATTERN.sub("", text)
    # 去除首尾空白与点
    text = text.strip().strip(".").strip()
    if not text:
        text = "Unknown"
    # 处理保留名
    stem, dot, _ = text.partition(".")
    if stem.upper() in _RESERVED_NAMES:
        text = f"_{text}"
    # 限制长度
    if len(text) > _MAX_NAME_LENGTH:
        text = text[:_MAX_NAME_LENGTH]
    return text


def _safe_get(data: Dict[str, Any], key: str, default: str = "Unknown") -> str:
    """安全获取字典值，None 或空字符串返回默认值。"""
    val = data.get(key, default)
    if val is None:
        return default
    val = str(val).strip()
    return val if val else default


def render_template(template: str, data: Dict[str, Any]) -> str:
    """根据模板渲染目标相对路径。

    支持变量：{artist} {album} {title} {year} {ext}
    以及格式化语法：{track:02d}（两位补零音轨号）。

    每个路径段（被 / 分隔）会单独清理非法字符，确保目录名与文件名合法。
    """
    # 准备变量，缺失则用 "Unknown"
    variables: Dict[str, Any] = {
        "artist": _safe_get(data, "artist", "Unknown Artist"),
        "album": _safe_get(data, "album", "Unknown Album"),
        "title": _safe_get(data, "title", "Unknown Title"),
        "year": _safe_get(data, "year", "") or "",
        "ext": _safe_get(data, "ext", "mp3").lower().lstrip("."),
    }

    # 处理音轨号：支持 {track:02d} 形式，无音轨号时用 0
    track = data.get("track_number")
    try:
        track_int = int(track) if track not in (None, "") else 0
    except (TypeError, ValueError):
        track_int = 0
    variables["track"] = track_int

    # 用 format_map 渲染（缺失键用 Unknown 填充，避免 KeyError）
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:  # type: ignore[override]
            return "Unknown"

    safe_vars = _SafeDict(variables)

    try:
        rendered = template.format_map(safe_vars)
    except (KeyError, IndexError, ValueError):
        # 模板格式错误时退回默认模板
        rendered = "{artist}/{album}/{track:02d}-{title}.{ext}".format_map(safe_vars)

    # 按路径分隔符分段，逐段清理非法字符
    # 注意：分隔符 / 在渲染后属于路径分隔，应保留
    segments = rendered.split("/")
    clean_segments = [sanitize_filename(seg) for seg in segments if seg.strip()]
    return "/".join(clean_segments)
