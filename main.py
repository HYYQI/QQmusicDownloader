"""QQ音乐下载器 - 命令行交互主程序"""

import os
import sys
import re

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from api.search import search_songs, display_search_results
from api.lyric import get_lyric, save_lyric
from api.audio import get_audio_url, download_audio
from converter import convert_to_mp3, check_ffmpeg, cleanup_original
from utils.logger import log


DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "downloads")


def sanitize_filename(name: str) -> str:
    """
    清理文件名中的非法字符。

    Args:
        name: 原始文件名

    Returns:
    合法的文件名
    """
    # 移除 Windows/Linux 文件名中不允许的字符
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    # 移除首尾空白和点号
    name = name.strip().strip('.')
    # 替换连续空白为单个空格
    name = re.sub(r'\s+', ' ', name)
    if not name:
        name = "unknown"
    return name


def build_filename(songname: str, singers: list, ext: str) -> str:
    """
    按照 "歌名-歌手" 格式构建文件名。

    Args:
        songname: 歌名
        singers: 歌手列表
        ext: 文件扩展名 (如 .mp3, .lrc)

    Returns:
    完整文件名
    """
    singer_str = ",".join(singers) if singers else "未知歌手"
    base = sanitize_filename(f"{songname}-{singer_str}")
    return f"{base}{ext}"


def prompt_search() -> str:
    """提示用户输入搜索关键词。"""
    print()
    keyword = input("请输入搜索关键词 (输入 q 退出): ").strip()
    return keyword


def prompt_selection(total: int) -> int:
    """
    提示用户选择歌曲序号。

    Args:
        total: 可选歌曲总数

    Returns:
    用户选择的序号 (1-based), 0 表示返回, -1 表示退出
    """
    while True:
        choice = input(f"请输入序号选择歌曲 (1-{total}, 0=重新搜索, q=退出): ").strip()
        if choice.lower() == 'q':
            return -1
        if choice == '0':
            return 0
        try:
            idx = int(choice)
            if 1 <= idx <= total:
                return idx
            else:
                print(f"请输入 1-{total} 之间的数字。")
        except ValueError:
            print("请输入有效数字。")


def download_song(song_info: dict) -> bool:
    """
    下载单首歌曲 (歌词 + 音频 + 转换)。

    Args:
        song_info: 歌曲信息字典

    Returns:
    成功返回 True, 否则 False
    """
    songmid = song_info["songmid"]
    songname = song_info["songname"]
    singers = song_info["singers"]

    print(f"\n准备下载: {songname} - {','.join(singers)}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # 1. 获取并保存歌词
    lyric_text = get_lyric(songmid)
    lrc_saved = False
    if lyric_text:
        lrc_filename = build_filename(songname, singers, ".lrc")
        lrc_path = os.path.join(DOWNLOAD_DIR, lrc_filename)
        lrc_saved = save_lyric(lyric_text, lrc_path)
        if lrc_saved:
            print(f"  歌词已保存: {lrc_filename}")
    else:
        print("  歌词获取失败, 跳过")

    # 2. 获取音频链接
    audio_result = get_audio_url(songmid)
    if not audio_result:
        print("  音频链接获取失败, 可能是VIP歌曲且未登录")
        log.warning("音频链接获取失败, songmid=%s, songname=%s", songmid, songname)
        return False

    audio_url, orig_filename = audio_result

    # 3. 下载原始音频 (m4a/aac)
    orig_ext = os.path.splitext(orig_filename)[1]  # .m4a or .aac
    if not orig_ext:
        orig_ext = ".m4a"
    orig_filename_new = build_filename(songname, singers, orig_ext)
    orig_path = os.path.join(DOWNLOAD_DIR, orig_filename_new)

    if not download_audio(audio_url, orig_path):
        print("  音频下载失败")
        return False

    print(f"  原始音频已保存: {orig_filename_new}")

    # 4. 转换为 mp3
    mp3_filename = build_filename(songname, singers, ".mp3")
    mp3_path = os.path.join(DOWNLOAD_DIR, mp3_filename)

    mp3_result = convert_to_mp3(orig_path, mp3_path)
    if mp3_result:
        print(f"  MP3 已保存: {mp3_filename}")
        # 删除原始文件
        cleanup_original(orig_path)
    else:
        print("  MP3 转换失败, 保留原始音频文件")
        print(f"  请手动安装 ffmpeg 后重试转换: sudo apt install ffmpeg")

    # 输出下载结果汇总
    print(f"\n  --- 下载结果 ---")
    print(f"  歌曲: {songname} - {','.join(singers)}")
    if lrc_saved:
        lrc_filename = build_filename(songname, singers, ".lrc")
        print(f"  歌词: {os.path.join(DOWNLOAD_DIR, lrc_filename)}")
    if mp3_result:
        print(f"  音频: {mp3_path}")
    else:
        print(f"  音频(原始): {orig_path}")
    print(f"  ----------------")

    return True


def main():
    """主程序入口。"""
    print("=" * 50)
    print("  QQ音乐下载器")
    print("  歌词和音频文件名格式: 歌名-歌手")
    print("  音频自动转换为 MP3 格式")
    print("=" * 50)

    # 检查 ffmpeg
    ffmpeg_available = check_ffmpeg()
    if not ffmpeg_available:
        print()
        print("[警告] 未检测到 ffmpeg, 音频转换功能将不可用。")
        print("       安装方法: sudo apt install ffmpeg (Linux)")
        print("       安装后音频将自动从 m4a/aac 转换为 mp3 格式。")
        print()

    while True:
        keyword = prompt_search()
        if not keyword:
            print("关键词不能为空。")
            continue
        if keyword.lower() == 'q':
            print("再见!")
            break

        # 搜索
        results = search_songs(keyword, num=15)
        if results is None:
            print("搜索请求失败, 请检查网络连接后重试。")
            continue
        if not results:
            print("未找到相关歌曲, 请换个关键词试试。")
            continue

        # 展示结果
        display_search_results(results)

        # 选择歌曲
        while True:
            choice = prompt_selection(len(results))
            if choice == -1:
                print("再见!")
                return
            if choice == 0:
                break  # 重新搜索

            selected = results[choice - 1]
            log.info("用户选择: %s - %s", selected["songname"], ",".join(selected["singers"]))

            # 下载
            success = download_song(selected)
            if not success:
                print("下载未完成, 可尝试其他歌曲。")

            # 下载完后, 询问是否继续
            next_action = input("\n输入 c 继续下载当前搜索结果, s 重新搜索, q 退出: ").strip().lower()
            if next_action == 'q':
                print("再见!")
                return
            elif next_action == 's':
                break  # 回到外层循环重新搜索
            elif next_action == 'c':
                continue  # 继续在当前结果中选择
            else:
                break  # 默认重新搜索


if __name__ == "__main__":
    main()
