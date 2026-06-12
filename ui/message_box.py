"""聊天消息气泡渲染模块。

MessageBox 负责将单条聊天消息（用户输入或宠物回复）按指定宽度
换行，并绘制为带背景色的圆角气泡，供 ui.chat_window.ChatWindow
渲染消息历史时使用。
"""

from __future__ import annotations

from typing import List

import pygame

# 用户消息 / 宠物消息的气泡背景色
USER_BUBBLE_COLOR = (210, 235, 255)
PET_BUBBLE_COLOR = (255, 230, 240)
TEXT_COLOR = (40, 40, 40)

PADDING = 8
LINE_HEIGHT = 18


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> List[str]:
    """按 max_width（像素）对文本进行换行。

    逐字符累加宽度，兼容中英文混排；显式换行符 "\\n" 会强制断行。
    """
    lines: List[str] = []
    current = ""

    for char in text:
        if char == "\n":
            lines.append(current)
            current = ""
            continue

        candidate = current + char
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate

    lines.append(current)
    return lines


class MessageBox:
    """单条聊天消息的气泡：换行后的文本 + 背景色绘制。"""

    def __init__(self, font: pygame.font.Font, sender: str, text: str, max_width: int) -> None:
        self.font = font
        self.sender = sender
        self.max_width = max_width
        self.lines = wrap_text(font, text, max_width - 2 * PADDING)

    @property
    def height(self) -> int:
        """气泡渲染所占的总高度（像素）。"""
        return len(self.lines) * LINE_HEIGHT + 2 * PADDING

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        """在 (x, y) 处绘制气泡（左上角坐标）。"""
        color = USER_BUBBLE_COLOR if self.sender == "user" else PET_BUBBLE_COLOR
        content_width = max((self.font.size(line)[0] for line in self.lines), default=0)
        width = min(content_width + 2 * PADDING, self.max_width)

        rect = pygame.Rect(x, y, width, self.height)
        pygame.draw.rect(surface, color, rect, border_radius=8)

        for index, line in enumerate(self.lines):
            text_surface = self.font.render(line, True, TEXT_COLOR)
            surface.blit(text_surface, (x + PADDING, y + PADDING + index * LINE_HEIGHT))
