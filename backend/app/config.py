"""应用配置管理。

从环境变量读取基础配置，并支持将可变配置（如整理任务参数）持久化到 config.json。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

# 应用根目录（backend/ 目录）
BASE_DIR = Path(__file__).resolve().parent.parent
# 数据目录
DATA_DIR = Path(os.environ.get("MUSIC_DATA_DIR", BASE_DIR / "data"))
# 配置文件路径（支持通过环境变量指定，便于 Docker 持久化）
CONFIG_FILE = Path(os.environ.get("CONFIG_FILE", str(DATA_DIR / "config.json")))


class Settings:
    """全局配置项（从环境变量读取，启动时确定）。"""

    # 服务监听
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "28081"))
    RELOAD: bool = os.environ.get("RELOAD", "false").lower() == "true"

    # 音乐目录
    MUSIC_INPUT_DIR: str = os.environ.get("MUSIC_INPUT_DIR", "/music")
    MUSIC_OUTPUT_DIR: str = os.environ.get("MUSIC_OUTPUT_DIR", "/music")
    MUSIC_RECYCLE_DIR: str = os.environ.get("MUSIC_RECYCLE_DIR", "/music/.recycle")

    # 数据库
    DB_PATH: str = os.environ.get("DB_PATH", str(DATA_DIR / "melodybox.db"))

    # 日志级别
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "info").lower()


# 默认整理配置（可被用户修改并持久化）
DEFAULT_ORGANIZE_CONFIG: Dict[str, Any] = {
    "inputDir": os.environ.get("MUSIC_INPUT_DIR", "/music"),
    "outputDir": os.environ.get("MUSIC_OUTPUT_DIR", "/music"),
    "recycleDir": os.environ.get("MUSIC_RECYCLE_DIR", "/music/.recycle"),
    "namingTemplate": "{artist}/{album}/{track:02d}-{title}.{ext}",
    "moveInsteadOfCopy": True,
    "overwritePolicy": "skip",  # skip | overwrite | rename
    "excludePatterns": [],  # 排除模式列表
}


def load_organize_config() -> Dict[str, Any]:
    """从 config.json 读取整理配置，不存在则返回默认配置。"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 与默认配置合并，保证新增字段有默认值
            merged = dict(DEFAULT_ORGANIZE_CONFIG)
            merged.update(data.get("organize", {}))
            return merged
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULT_ORGANIZE_CONFIG)
    return dict(DEFAULT_ORGANIZE_CONFIG)


def save_organize_config(config: Dict[str, Any]) -> None:
    """将整理配置持久化到 config.json。"""
    data: Dict[str, Any] = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    data["organize"] = config
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_data_dir() -> None:
    """确保数据目录存在（用于存放 SQLite 数据库）。"""
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)


# 全局配置单例
settings = Settings()
