"""日志模块 - 统一管理项目日志"""

import logging
import os
import sys
from datetime import datetime


def setup_logger(name: str = "qq_music_dl", log_dir: str = None) -> logging.Logger:
    """
    创建并配置日志记录器。

    Args:
        name: 日志记录器名称
        log_dir: 日志文件存放目录, 默认为项目根目录下的 logs/

    Returns:
        配置好的 Logger 实例
    """
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 防止重复添加 handler
    if logger.handlers:
        return logger

    # 日志文件名按日期
    log_file = os.path.join(
        log_dir,
        f"{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    # 文件 handler - 记录所有级别
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # 控制台 handler - 仅 INFO 及以上
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s"
    ))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


# 全局默认日志记录器
log = setup_logger()
