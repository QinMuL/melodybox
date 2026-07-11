"""艺术家头像获取服务。

通过 MusicBrainz 搜索艺术家 MBID，再通过 Wikipedia API 获取艺术家照片。
获取到的图片缓存到 /app/data/covers/artists/{artist_id}.jpg
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


def _fetch_wikipedia_image(page_title: str, lang: str = "zh") -> Optional[tuple[bytes, str]]:
    """通过 Wikipedia API 获取页面缩略图。"""
    import urllib.request
    import json

    titles = quote(page_title)
    url = (
        f"https://{lang}.wikipedia.org/w/api.php?"
        f"action=query&titles={titles}&prop=pageimages&format=json"
        f"&pithumbsize=300&pilicense=any"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MelodyBox/0.1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {})
            if thumb and "source" in thumb:
                img_url = thumb["source"]
                # 下载图片
                img_req = urllib.request.Request(img_url, headers={"User-Agent": "MelodyBox/0.1.0"})
                with urllib.request.urlopen(img_req, timeout=15) as img_resp:
                    img_data = img_resp.read()
                if len(img_data) > 100:
                    mime = img_resp.headers.get("Content-Type", "image/jpeg")
                    return img_data, mime
    except Exception as exc:  # noqa: BLE001
        logger.debug("Wikipedia 获取图片失败 (%s): %s", page_title, exc)
    return None


def fetch_artist_image(artist_name: str) -> Optional[tuple[bytes, str]]:
    """通过 MusicBrainz + Wikipedia 获取艺术家头像。

    策略：
    1. 对于多艺人（含 &），只搜索第一个艺人
    2. 用 MusicBrainz 搜索获取 MBID 和别名
    3. 依次用原名、别名、英文名搜索 Wikipedia（中英文）
    """
    try:
        import musicbrainzngs

        musicbrainzngs.set_useragent(
            "MelodyBox",
            "0.1.0",
            "https://github.com/QinMuL/melodybox",
        )

        # 多艺人拆分：只搜索第一个
        search_name = artist_name.split("&")[0].split(",")[0].strip()
        if not search_name:
            search_name = artist_name

        # 1. 搜索艺术家获取 MBID
        result = musicbrainzngs.search_artists(artist=search_name, limit=1)
        artists = result.get("artist-list", [])
        if not artists:
            logger.debug("MusicBrainz 未找到艺术家: %s", search_name)
            # 回退：直接搜索 Wikipedia
            for lang in ["zh", "en"]:
                img = _fetch_wikipedia_image(search_name, lang)
                if img:
                    return img
            return None

        mbid = artists[0]["id"]
        logger.info("MusicBrainz 找到 %s → MBID: %s", search_name, mbid)

        # 2. 查询详情获取 Wikipedia URL 和别名
        detail = musicbrainzngs.get_artist_by_id(mbid, includes=["url-rels", "aliases"])

        # 收集所有可用于搜索的名字
        search_names = [search_name]
        # 添加别名
        for alias in detail.get("alias-list", []):
            alias_name = alias.get("name", "")
            if alias_name and alias.get("locale", "").startswith("en"):
                search_names.append(alias_name)
        # 添加 MusicBrainz 中的名字
        mb_name = detail.get("name", "")
        if mb_name and mb_name not in search_names:
            search_names.append(mb_name)

        # 收集 Wikipedia URL
        wiki_pages = []
        for rel in detail.get("url-relation-list", []):
            target = rel.get("target", "")
            if "wikipedia" in target:
                title = target.split("/wiki/")[-1] if "/wiki/" in target else ""
                if title:
                    wiki_pages.append((title, "zh" if "zh.wikipedia" in target else "en"))

        # 3. 优先从 Wikipedia URL 获取图片
        for title, lang in wiki_pages:
            img = _fetch_wikipedia_image(title, lang)
            if img:
                logger.info("Wikipedia(URL)获取到 %s 的头像", artist_name)
                return img

        # 4. 用各种名字搜索 Wikipedia
        for name in search_names:
            for lang in ["zh", "en"]:
                img = _fetch_wikipedia_image(name, lang)
                if img:
                    logger.info("Wikipedia(%s,%s)获取到 %s 的头像", name, lang, artist_name)
                    return img

    except Exception as exc:  # noqa: BLE001
        logger.warning("获取艺术家头像失败 %s: %s", artist_name, exc)
    return None


def save_artist_avatar(artist_id: str, artist_name: str) -> bool:
    """获取并保存艺术家头像到磁盘。返回是否成功。"""
    from app.config import DATA_DIR

    avatars_dir = DATA_DIR / "covers" / "artists"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # 已存在则跳过
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        if (avatars_dir / f"{artist_id}{ext}").exists():
            return True

    result = fetch_artist_image(artist_name)
    if result is None:
        return False

    data, mime = result
    ext = ".png" if "png" in mime else ".jpg"
    avatar_file = avatars_dir / f"{artist_id}{ext}"
    try:
        with open(avatar_file, "wb") as f:
            f.write(data)
        logger.info("保存艺术家头像: %s → %s", artist_name, avatar_file)
        return True
    except OSError as exc:
        logger.warning("保存艺术家头像失败: %s", exc)
    return False
