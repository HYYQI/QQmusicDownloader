"""歌词模块 - 获取歌曲歌词"""

import requests
import re
import json
from typing import Optional

from utils.logger import log

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://y.qq.com/"
}

COOKIES = {
    # 如有登录 Cookie 可在此填写
}


def get_lyric(songmid: str) -> Optional[str]:
    """
    通过 songmid 获取歌词文本。

    Args:
        songmid: 歌曲MID

    Returns:
        歌词文本(LRC格式), 获取失败返回 None
    """
    log.info("正在获取歌词, songmid=%s", songmid)

    url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
    params = {
        "songmid": songmid,
        "format": "json",
        "nobase64": "1"
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, cookies=COOKIES, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error("歌词请求失败: %s", e)
        return None

    # 剥离可能的 JSONP 外壳
    text = re.sub(r'^\w+\((.*)\)$', r'\1', resp.text, flags=re.DOTALL)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        log.error("歌词JSON解析失败: %s", e)
        log.debug("原始响应: %s", resp.text[:300])
        return None

    retcode = data.get("retcode", -1)
    if retcode != 0:
        log.warning("歌词接口返回非零 retcode: %s", retcode)

    lyric = data.get("lyric", "")
    if lyric:
        log.info("歌词获取成功, 长度=%d", len(lyric))
        return lyric
    else:
        log.warning("接口返回中无歌词内容")
        return None


def save_lyric(lyric_text: str, filepath: str) -> bool:
    """
    将歌词保存到文件。

    Args:
        lyric_text: LRC格式歌词文本
        filepath: 保存路径

    Returns:
        保存成功返回 True, 否则 False
    """
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(lyric_text)
        log.info("歌词已保存到: %s", filepath)
        return True
    except OSError as e:
        log.error("歌词保存失败: %s", e)
        return False
