"""音频元数据读取服务（基于 mutagen）。

支持格式：MP3, FLAC, APE, WAV, M4A, OGG, OPUS
返回统一结构，缺失字段用 "Unknown" 填充。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 各格式常见的标签键（小写匹配）
_TAG_KEYS = {
    "title": ["title", "tit2"],
    "artist": ["artist", "tpe1", "albumartist", "tpe2"],
    "album": ["album", "talb"],
    "track_number": ["tracknumber", "track", "trck"],
    "year": ["date", "year", "tdrc", "tyer"],
}


def _first_tag(tags: Any, keys: list[str]) -> Optional[str]:
    """从 mutagen 标签对象中按候选键名取值。

    mutagen 对多值字段（如多艺人）返回列表，此时用 ' & ' 连接所有非空值。
    """
    if not tags:
        return None
    # mutagen 标签键通常区分大小写，这里做大小写不敏感查找
    lower_map: Dict[str, Any] = {}
    if hasattr(tags, "keys"):
        for k in tags.keys():
            lower_map[k.lower()] = tags[k]
    for key in keys:
        if key in lower_map:
            val = lower_map[key]
            # mutagen 返回的值可能是列表（多艺人等）
            if isinstance(val, list):
                if not val:
                    continue
                # 用 ' & ' 连接所有非空值
                parts = [str(v).strip() for v in val if v]
                if parts:
                    return " & ".join(parts)
                continue
            return str(val).strip() if val is not None else None
    return None


def _parse_int(value: Any) -> Optional[int]:
    """从字符串中解析整数（如 '3/12' 取 3）。"""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # 处理 "3/12" 形式
    s = s.split("/")[0].strip()
    try:
        return int(s)
    except ValueError:
        return None


def _parse_year(value: Any) -> Optional[int]:
    """从字符串中解析年份（取前 4 位数字）。"""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # 提取前 4 位数字
    digits = ""
    for ch in s:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    if len(digits) >= 4:
        try:
            return int(digits[:4])
        except ValueError:
            return None
    return None


def read_metadata(file_path: str) -> Dict[str, Any]:
    """读取音频文件元数据，返回统一结构。

    Args:
        file_path: 音频文件绝对路径

    Returns:
        包含 title, artist, album, track_number, year, duration,
        format, bitrate, sample_rate, channels 的字典。
        读取失败时返回带 "Unknown" 的默认结构。
    """
    from app.utils.file_utils import get_audio_format

    # 默认结构
    result: Dict[str, Any] = {
        "title": "Unknown",
        "artist": "Unknown",
        "album": "Unknown",
        "track_number": None,
        "year": None,
        "duration": 0.0,
        "format": get_audio_format(file_path) or "unknown",
        "bitrate": None,
        "sample_rate": None,
        "channels": None,
    }

    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(file_path, easy=False)
        if audio is None:
            logger.warning("无法识别音频文件: %s", file_path)
            return result

        # 读取标签
        tags = getattr(audio, "tags", None)
        result["title"] = _first_tag(tags, _TAG_KEYS["title"]) or "Unknown"
        result["artist"] = _first_tag(tags, _TAG_KEYS["artist"]) or "Unknown"
        result["album"] = _first_tag(tags, _TAG_KEYS["album"]) or "Unknown"
        result["track_number"] = _parse_int(
            _first_tag(tags, _TAG_KEYS["track_number"])
        )
        result["year"] = _parse_year(_first_tag(tags, _TAG_KEYS["year"]))

        # 读取音频信息
        info = getattr(audio, "info", None)
        if info is not None:
            # 时长（秒）
            duration = getattr(info, "length", None)
            if duration is not None:
                try:
                    result["duration"] = float(duration)
                except (TypeError, ValueError):
                    result["duration"] = 0.0
            # 比特率
            bitrate = getattr(info, "bitrate", None)
            if bitrate is not None:
                try:
                    # mutagen 的 bitrate 单位是 bps，转为 kbps
                    result["bitrate"] = int(bitrate // 1000)
                except (TypeError, ValueError, ZeroDivisionError):
                    result["bitrate"] = None
            # 采样率
            sample_rate = getattr(info, "sample_rate", None)
            if sample_rate is not None:
                try:
                    result["sample_rate"] = int(sample_rate)
                except (TypeError, ValueError):
                    result["sample_rate"] = None
            # 声道数
            channels = getattr(info, "channels", None)
            if channels is not None:
                try:
                    result["channels"] = int(channels)
                except (TypeError, ValueError):
                    result["channels"] = None
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取元数据失败 %s: %s", file_path, exc)

    return result


def extract_cover(file_path: str) -> Optional[tuple[bytes, str]]:
    """从音频文件中提取嵌入式封面图。

    Returns:
        (图片二进制数据, MIME类型) 或 None
    """
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(file_path, easy=False)
        if audio is None:
            return None

        # 通用接口：audio.pictures（FLAC/OGG/OPUS 等）
        pictures = getattr(audio, "pictures", None)
        if pictures:
            for pic in pictures:
                if pic.type == 3:  # front cover
                    return pic.data, pic.mime
            # 没有 front cover 就用第一张
            pic = pictures[0]
            return pic.data, pic.mime

        # ID3 (MP3)：APIC 帧
        tags = getattr(audio, "tags", None)
        if tags:
            for key in tags:
                if str(key).upper().startswith("APIC"):
                    frame = tags[key]
                    if hasattr(frame, "data") and hasattr(frame, "mime"):
                        return frame.data, frame.mime

        # MP4/M4A：covr
        if tags and "covr" in tags:
            covr = tags["covr"]
            if covr:
                mime = "image/jpeg"
                if hasattr(covr[0], "imageformat"):
                    from mutagen.mp4 import MP4Cover
                    if covr[0].imageformat == MP4Cover.FORMAT_PNG:
                        mime = "image/png"
                return bytes(covr[0]), mime
    except Exception as exc:  # noqa: BLE001
        logger.debug("提取封面失败 %s: %s", file_path, exc)
    return None


def get_duration(file_path: str) -> float:
    """仅读取音频时长（秒）。"""
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(file_path)
        if audio and hasattr(audio, "info"):
            return float(getattr(audio.info, "length", 0.0) or 0.0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取时长失败 %s: %s", file_path, exc)
    return 0.0
