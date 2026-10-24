"""转换模块 - 将 m4a/aac 等格式转换为 mp3"""

import os
import subprocess
from typing import Optional

from utils.logger import log


def check_ffmpeg() -> bool:
    """
    检查系统中是否安装了 ffmpeg。

    Returns:
        已安装返回 True, 否则 False
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n")[0]
            log.info("检测到 ffmpeg: %s", version_line)
            return True
        return False
    except FileNotFoundError:
        log.warning("未检测到 ffmpeg, 请先安装 ffmpeg")
        return False
    except subprocess.TimeoutExpired:
        log.warning("ffmpeg 检测超时")
        return False


def convert_to_mp3(input_path: str, output_path: Optional[str] = None,
                   bitrate: str = "192k") -> Optional[str]:
    """
    将音频文件转换为 mp3 格式。

    Args:
        input_path: 输入文件路径 (m4a/aac 等格式)
        output_path: 输出文件路径, 默认与输入同目录, 扩展名改为 .mp3
        bitrate: MP3 比特率, 默认 192k

    Returns:
        转换成功返回输出文件路径, 否则返回 None
    """
    if not os.path.isfile(input_path):
        log.error("输入文件不存在: %s", input_path)
        return None

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".mp3"

    log.info("正在转换: %s -> %s (bitrate=%s)", input_path, output_path, bitrate)

    # 优先尝试使用 ffmpeg (subprocess)
    if check_ffmpeg():
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ab", bitrate,
                "-map_metadata", "0",
                output_path
            ]
            log.debug("执行命令: %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and os.path.isfile(output_path):
                log.info("转换完成(ffmpeg): %s", output_path)
                return output_path
            else:
                log.error("ffmpeg 转换失败: %s", result.stderr[:300])
                return None

        except subprocess.TimeoutExpired:
            log.error("ffmpeg 转换超时")
            return None
        except Exception as e:
            log.error("ffmpeg 转换异常: %s", e)
            return None

    # ffmpeg 不可用, 尝试使用 pydub (内部也依赖 ffmpeg)
    try:
        from pydub import AudioSegment
        log.info("尝试使用 pydub 进行转换...")
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="mp3", bitrate=bitrate)
        log.info("转换完成(pydub): %s", output_path)
        return output_path
    except Exception as e:
        log.error("pydub 转换失败: %s", e)
        log.error("请确保已安装 ffmpeg 并添加到 PATH, 或使用: sudo apt install ffmpeg")
        return None


def cleanup_original(input_path: str) -> bool:
    """
    转换成功后删除原始文件。

    Args:
        input_path: 原始文件路径

    Returns:
        删除成功返回 True, 否则 False
    """
    try:
        os.remove(input_path)
        log.info("已删除原始文件: %s", input_path)
        return True
    except OSError as e:
        log.warning("删除原始文件失败: %s", e)
        return False
