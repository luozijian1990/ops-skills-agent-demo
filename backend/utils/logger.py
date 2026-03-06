"""
最简洁的全局 logger - Go 语言风格
"""

import os
import sys
from loguru import logger as _logger


def init_logger():
    """初始化全局 logger，从 config 统一读取配置"""
    from config import LOG_LEVEL, LOG_FILE, LOG_MAX_SIZE_MB, LOG_BACKUP_COUNT

    # 移除默认处理器
    _logger.remove()

    level = LOG_LEVEL.upper()

    # 控制台配置
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    _logger.add(sys.stderr, format=console_format, level=level, colorize=True)

    # 文件配置
    if LOG_FILE:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        )

        _logger.add(
            LOG_FILE,
            format=file_format,
            level=level,
            rotation=LOG_MAX_SIZE_MB * 1024 * 1024,  # MB 转字节
            retention=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )

    _logger.info(f"日志系统已初始化 (level={level}, file={LOG_FILE})")
    return _logger


# 默认初始化
logger = init_logger()


__all__ = ["logger"]
