"""文件操作工具：哈希计算、音频文件发现、目录操作。"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import List, Set

# 支持的音频格式扩展名（小写，含点）
AUDIO_EXTENSIONS: Set[str] = {
    ".mp3", ".flac", ".ape", ".wav", ".m4a", ".ogg", ".opus",
}

# 缓冲区大小（用于哈希计算）
_HASH_CHUNK_SIZE = 64 * 1024


def is_audio_file(path: str | Path) -> bool:
    """判断给定路径是否为支持的音频文件。"""
    p = Path(path)
    if not p.is_file():
        return False
    return p.suffix.lower() in AUDIO_EXTENSIONS


def get_audio_format(path: str | Path) -> str:
    """从文件路径获取音频格式名（小写，无点）。"""
    return Path(path).suffix.lower().lstrip(".")


def find_audio_files(
    directory: str | Path,
    exclude_patterns: List[str] | None = None,
) -> List[str]:
    """递归扫描目录下所有支持的音频文件。

    Args:
        directory: 扫描根目录
        exclude_patterns: 排除模式列表（对相对路径做子串匹配）

    Returns:
        音频文件绝对路径列表（已排序）
    """
    root = Path(directory)
    exclude_patterns = exclude_patterns or []
    if not root.exists() or not root.is_dir():
        return []

    results: List[str] = []
    for path in sorted(root.rglob("*")):
        if not is_audio_file(path):
            continue
        rel = str(path.relative_to(root))
        # 应用排除模式（子串匹配）
        if any(pattern and pattern in rel for pattern in exclude_patterns):
            continue
        results.append(str(path))
    return results


def compute_file_hash(path: str | Path) -> str:
    """计算文件 MD5 哈希。"""
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def file_size(path: str | Path) -> int:
    """获取文件大小（字节），文件不存在返回 0。"""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在，不存在则创建。"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def unique_path(target: Path) -> Path:
    """为目标路径生成一个不冲突的路径（加数字后缀）。"""
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def move_file(source: str | Path, target: str | Path) -> str:
    """移动文件到目标路径（自动创建父目录）。

    返回最终目标路径字符串。
    """
    src = Path(source)
    dst = Path(target)
    ensure_dir(dst.parent)
    shutil.move(str(src), str(dst))
    return str(dst)


def copy_file(source: str | Path, target: str | Path) -> str:
    """复制文件到目标路径（自动创建父目录）。

    返回最终目标路径字符串。
    """
    src = Path(source)
    dst = Path(target)
    ensure_dir(dst.parent)
    shutil.copy2(str(src), str(dst))
    return str(dst)


def move_to_recycle(source: str | Path, recycle_dir: str | Path) -> str:
    """将文件移动到回收站目录（保留相对路径结构，避免重名冲突）。"""
    src = Path(source)
    recycle = Path(recycle_dir)
    # 用文件名 + 唯一后缀避免冲突
    target = unique_path(recycle / src.name)
    return move_file(src, target)


def delete_file(path: str | Path) -> bool:
    """删除文件，返回是否成功。"""
    try:
        Path(path).unlink()
        return True
    except OSError:
        return False


def is_dir_accessible(path: str | Path) -> bool:
    """检查目录是否可访问（存在且可读）。"""
    p = Path(path)
    return p.exists() and p.is_dir() and os.access(p, os.R_OK)


def is_dir_writable(path: str | Path) -> bool:
    """检查目录是否可写。"""
    p = Path(path)
    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
    return os.access(p, os.W_OK)
