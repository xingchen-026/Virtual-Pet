"""交互提示 UI 模块。

管理屏幕上短暂显示的提示文字（例如 "+5 Mood"），
提示会在显示一段时间后自动消失，不阻塞游戏主循环。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

DEFAULT_FEEDBACK_DURATION = 1.2
DEFAULT_FEEDBACK_COLOR = (220, 80, 80)


@dataclass
class _FeedbackMessage:
    """单条提示文字及其剩余显示时间。"""

    text: str
    remaining: float


class FeedbackOverlay:
    """管理多条提示文字的显示、倒计时与自动消失。"""

    def __init__(
        self,
        font: pygame.font.Font,
        color: Tuple[int, int, int] = DEFAULT_FEEDBACK_COLOR,
        default_duration: float = DEFAULT_FEEDBACK_DURATION,
    ) -> None:
        self.font = font
        self.color = color
        self.default_duration = default_duration
        self._messages: List[_FeedbackMessage] = []

    def show(self, text: str, duration: Optional[float] = None) -> None:
        """添加一条提示文字。空字符串将被忽略，不产生提示。"""
        if not text:
            return

        self._messages.append(
            _FeedbackMessage(text=text, remaining=duration if duration is not None else self.default_duration)
        )

    def update(self, dt: float) -> None:
        """推进所有提示的倒计时，并移除已过期的提示。"""
        for message in self._messages:
            message.remaining -= dt

        self._messages = [message for message in self._messages if message.remaining > 0]

    def draw(self, screen: pygame.Surface, position: Tuple[int, int], line_height: int = 20) -> None:
        """在指定位置依次绘制当前所有提示文字。"""
        x, y = position
        for message in self._messages:
            surface = self.font.render(message.text, True, self.color)
            screen.blit(surface, (x, y))
            y += line_height
