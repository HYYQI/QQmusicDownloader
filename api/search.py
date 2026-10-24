"""搜索模块 - 通过关键词搜索歌曲"""

import requests
import json
from typing import List, Dict, Optional

from utils.logger import log

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://y.qq.com/"
}

COOKIES = {
    # 如有登录 Cookie 可在此填写, 提高获取 VIP 音频的成功率
    # "uin": "...",
    # "qqmusic_key": "..."
}


def search_songs(keyword: str, page: int = 1, num: int = 10) -> Optional[List[Dict]]:
    """
    通过关键词搜索歌曲, 返回歌曲信息列表。

    Args:
        keyword: 搜索关键词
        page: 页码, 从1开始
        num: 每页返回数量, 最大30

    Returns:
        歌曲信息字典列表, 每项包含:
          - songmid: 歌曲MID
          - songname: 歌名
          - singers: 歌手列表 (字符串列表)
          - albumname: 专辑名
          - albummid: 专辑MID
          - interval: 时长(秒)
          - pay: 付费信息字典
          - songid: 歌曲ID
        搜索失败时返回 None
    """
    log.info("正在搜索: %s ...", keyword)

    url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    params = {
        "w": keyword,
        "format": "json",
        "p": page,
        "n": num
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, cookies=COOKIES, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log.error("搜索请求失败: %s", e)
        return None
    except (json.JSONDecodeError, ValueError) as e:
        log.error("搜索结果解析失败: %s", e)
        return None

    try:
        song_list = data["data"]["song"]["list"]
    except (KeyError, IndexError, TypeError):
        log.error("搜索结果结构异常, 未找到歌曲列表")
        log.debug("原始返回: %s", json.dumps(data, ensure_ascii=False)[:500])
        return None

    if not song_list:
        log.warning("未找到与 '%s' 相关的歌曲", keyword)
        return []

    results = []
    for item in song_list:
        singers = [s.get("name", "") for s in item.get("singer", [])]
        song_info = {
            "songmid": item.get("songmid", ""),
            "songname": item.get("songname", ""),
            "singers": singers,
            "albumname": item.get("albumname", ""),
            "albummid": item.get("albummid", ""),
            "interval": item.get("interval", 0),
            "pay": item.get("pay", {}),
            "songid": item.get("songid", 0),
        }
        results.append(song_info)

    log.info("搜索完成, 共找到 %d 首歌曲", len(results))
    return results


def format_duration(seconds: int) -> str:
    """将秒数格式化为 mm:ss"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def display_search_results(results: List[Dict]) -> None:
    """
    格式化展示搜索结果。

    Args:
        results: search_songs 返回的歌曲信息列表
    """
    if not results:
        print("未找到相关歌曲。")
        return

    print()
    print("=" * 80)
    print(f"{'序号':<4} {'歌名':<30} {'歌手':<20} {'专辑':<20} {'时长'}")
    print("-" * 80)

    for i, song in enumerate(results):
        singer_str = "/".join(song["singers"])
        name = song["songname"]
        if len(name) > 28:
            name = name[:26] + ".."
        if len(singer_str) > 18:
            singer_str = singer_str[:16] + ".."
        album = song["albumname"]
        if len(album) > 18:
            album = album[:16] + ".."
        duration = format_duration(song["interval"])

        # 标记付费歌曲
        pay_info = song.get("pay", {})
        pay_mark = ""
        if pay_info.get("payplay", 0) == 1 or pay_info.get("paydownload", 0) == 1:
            pay_mark = " [VIP]"

        print(f"{i + 1:<4} {name:<30} {singer_str:<20} {album:<20} {duration}{pay_mark}")

    print("=" * 80)
