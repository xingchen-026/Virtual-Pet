"""宠物自主行为日志模块。

BehaviorLogger 将自主行为系统产生的事件以
"HH:MM:SS 描述" 的格式追加写入日志文件，
用于调试自主行为系统，不影响主循环运行。
"""

from __future__ import annotations

import os
import time


class BehaviorLogger:
    """将行为事件以时间戳追加写入日志文件。"""

    def __init__(self, log_file: str) -> None:
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log(self, message: str) -> None:
        """追加写入一条带时间戳的日志记录。"""
        timestamp = time.strftime("%H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {message}\n")
