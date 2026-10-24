"""音频模块 - 获取音频链接并下载"""

import requests
import json
import os
from urllib.parse import urljoin
from typing import Optional, Tuple

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


def get_audio_url(songmid: str) -> Optional[Tuple[str, str]]:
    """
    通过 songmid 获取音频下载链接和文件名。

    Args:
        songmid: 歌曲MID

    Returns:
        (音频下载URL, 原始文件名) 元组, 如 ("http://...", "C400xxx.m4a")
        获取失败返回 None
    """
    log.info("正在获取音频链接, songmid=%s", songmid)

    url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    payload = {
        "req": {
            "module": "vkey.GetVkeyServer",
            "method": "CgiGetVkey",
            "param": {
                "guid": "10000",
                "songmid": [songmid],
                "songtype": [0],
                "uin": COOKIES.get("uin", "0"),
                "loginflag": 1,
                "platform": "20"
            }
        }
    }

    post_headers = HEADERS.copy()
    post_headers["Content-Type"] = "application/json"

    try:
        resp = requests.post(url, headers=post_headers, json=payload, cookies=COOKIES, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log.error("音频链接请求失败: %s", e)
        return None
    except (json.JSONDecodeError, ValueError) as e:
        log.error("音频链接响应解析失败: %s", e)
        return None

    try:
        if data.get("code") != 0:
            log.error("vkey 接口返回错误码: %s", data.get("code"))
            return None

        midurlinfo = data["req"]["data"]["midurlinfo"][0]
        purl = midurlinfo.get("purl", "")
        filename = midurlinfo.get("filename", "")

        if purl:
            sip = data["req"]["data"]["sip"][0]
            audio_url = urljoin(sip, purl)
            log.info("音频链接获取成功, 文件名=%s", filename)
            return (audio_url, filename)
        else:
            result_code = midurlinfo.get("result", 0)
            log.error("无法获取音频链接 (可能是VIP歌曲且未登录), result=%s", result_code)
            return None
    except (KeyError, IndexError, TypeError) as e:
        log.error("解析音频链接失败: %s", e)
        log.debug("原始返回: %s", json.dumps(data, ensure_ascii=False)[:500])
        return None


def download_audio(audio_url: str, save_path: str) -> bool:
    """
    下载音频文件。

    Args:
        audio_url: 音频下载链接
        save_path: 保存路径 (含文件名)

    Returns:
        下载成功返回 True, 否则 False
    """
    log.info("正在下载音频到: %s", save_path)

    try:
        resp = requests.get(audio_url, headers=HEADERS, stream=True, timeout=30)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0

        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 简单进度显示
                    if total_size > 0:
                        percent = downloaded / total_size * 100
                        print(f"\r  下载进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="", flush=True)

        print()  # 换行
        log.info("音频下载完成, 文件大小=%d bytes", downloaded)
        return True

    except requests.RequestException as e:
        log.error("音频下载失败: %s", e)
        return False
    except OSError as e:
        log.error("音频文件写入失败: %s", e)
        return False
