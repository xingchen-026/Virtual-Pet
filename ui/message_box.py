"""聊天消息气泡渲染模块。

MessageBox 负责将单条聊天消息（用户输入或宠物回复）按指定宽度
换行，并绘制为带背景色的圆角气泡，供 ui.chat_window.ChatWindow
渲染消息历史时使用。
"""

from __future__ import annotations

from typing import List

import pygame

from ui import theme

PADDING = 8


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
        # 行高随字体变化（中文字体行高大于默认英文字体），避免行间重叠
        self.line_height = font.get_linesize()

        # 消息文本固定不变，预渲染各行 Surface，避免聊天窗口每帧重复 render
        self._line_surfaces = [font.render(line, True, theme.TEXT_COLOR) for line in self.lines]
        content_width = max((s.get_width() for s in self._line_surfaces), default=0)
        self._width = min(content_width + 2 * PADDING, self.max_width)

    @property
    def height(self) -> int:
        """气泡渲染所占的总高度（像素）。"""
        return len(self.lines) * self.line_height + 2 * PADDING

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        """在 (x, y) 处绘制气泡（左上角坐标）。"""
        color = theme.USER_BUBBLE_COLOR if self.sender == "user" else theme.PET_BUBBLE_COLOR

        rect = pygame.Rect(x, y, self._width, self.height)
        pygame.draw.rect(surface, color, rect, border_radius=8)

        for index, text_surface in enumerate(self._line_surfaces):
            surface.blit(text_surface, (x + PADDING, y + PADDING + index * self.line_height))
