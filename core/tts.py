"""语音朗读（TTS）模块。

TTSManager 用可选依赖 pyttsx3（离线，Windows 走 SAPI5）朗读宠物的主动发言与
聊天回复。设计原则：

* **完全可选 / 优雅降级**：未安装 pyttsx3 或引擎初始化失败时整体禁用，
  speak() 变为安全空操作，不影响桌宠其它功能。
* **单后台线程串行朗读**：引擎在专用 worker 线程创建并 runAndWait（朗读会阻塞），
  避免阻塞主循环；用队列串行化，队列积压时丢弃新请求，防止"抢话"与回放堆叠。
* 总开关 enabled 可运行时切换（设置窗口）。
"""

from __future__ import annotations

import queue
import threading

from utils.exception import AppError, log_exception

# 队列里最多缓冲的待朗读条数，超过则丢弃新请求（避免朗读严重滞后于气泡）
_MAX_PENDING = 1


class TTSManager:
    """后台串行朗读文本；pyttsx3 不可用时静默降级。"""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self._ok = False
        self._queue: "queue.Queue[str]" = queue.Queue()

        try:
            import pyttsx3  # noqa: F401  仅探测可用性，引擎在 worker 线程创建
        except Exception as exc:
            log_exception(AppError(f"TTS 不可用（未安装 pyttsx3），已禁用语音: {exc}"))
            return

        self._ok = True
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        """专用线程：创建引擎并循环朗读队列中的文本（runAndWait 阻塞于此线程）。"""
        try:
            import pyttsx3

            engine = pyttsx3.init()
        except Exception as exc:
            log_exception(AppError(f"TTS 引擎初始化失败，已禁用语音: {exc}"))
            self._ok = False
            return

        while True:
            text = self._queue.get()
            if not text:
                continue
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                log_exception(AppError(f"TTS 朗读异常（忽略本条）: {exc}"))

    def speak(self, text: str) -> None:
        """朗读一段文本；未启用/不可用/空文本/队列积压时安全跳过。"""
        if not self.enabled or not self._ok or not text:
            return
        if self._queue.qsize() <= _MAX_PENDING:
            self._queue.put(text)

    def set_enabled(self, enabled: bool) -> None:
        """运行时切换语音朗读开关。"""
        self.enabled = enabled
