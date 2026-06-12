"""统一异常处理模块。

定义桌宠应用专用的异常类型，并提供统一的日志记录与"安全执行"工具：

* 资源不存在 / 动画加载失败 -> ResourceLoadError / AnimationLoadError
* 存档损坏 -> SaveDataError
* 窗口初始化失败 -> DesktopWindowError

各模块在捕获到这些异常时调用 log_exception() 记录到
logs/error.log，并使用兜底数据继续运行，避免程序直接崩溃。
"""

from __future__ import annotations

import logging
import os

from config import settings

_LOG_FILE = os.path.join(settings.LOGS_DIR, "error.log")


class AppError(Exception):
    """桌宠应用异常基类。"""


class ResourceLoadError(AppError):
    """资源文件不存在或加载失败。"""


class AnimationLoadError(AppError):
    """动画帧加载失败。"""


class SaveDataError(AppError):
    """存档数据缺失或损坏。"""


class DesktopWindowError(AppError):
    """桌面窗口相关操作失败。"""


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("virtual_pet")
    logger.setLevel(logging.WARNING)

    if not logger.handlers:
        os.makedirs(settings.LOGS_DIR, exist_ok=True)
        handler = logging.FileHandler(_LOG_FILE, encoding="utf-8", delay=True)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

    return logger


_logger = _build_logger()


def log_exception(exc: Exception) -> None:
    """将异常信息记录到 logs/error.log，不中断程序运行。"""
    _logger.warning("%s: %s", type(exc).__name__, exc)
