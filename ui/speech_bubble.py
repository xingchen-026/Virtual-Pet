"""宠物头顶聊天气泡模块。

SpeechBubble 在宠物头顶绘制一个临时的圆角对话气泡，用于"休息提醒"
等主动提示。气泡显示固定时长后自动消失，不拦截任何输入事件，
也不属于 UIManager.is_active（不影响帧率档位与自主行为暂停）。

定位与渲染只依赖宠物精灵的矩形（anchor_rect），与具体业务对象解耦。
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.message_box import wrap_text

PADDING = 10
MAX_WIDTH = 240
# 气泡与宠物头顶之间的间距，以及底部小尾巴的高度
GAP = 10
TAIL_HEIGHT = 8
TAIL_WIDTH = 16


class SpeechBubble:
    """宠物头顶的临时圆角提示气泡。"""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self._text = ""
        self._timer = 0.0  # 剩余显示时间（秒）

    @property
    def visible(self) -> bool:
        return self._timer > 0

    def show(self, text: str, duration: float) -> None:
        """显示一条提示，持续 duration 秒（覆盖上一条）。"""
        self._text = text
        self._timer = duration

    def hide(self) -> None:
        self._timer = 0.0

    def update(self, dt: float) -> None:
        if self._timer > 0:
            self._timer = max(0.0, self._timer - dt)

    def draw(self, surface: pygame.Surface, anchor_rect: pygame.Rect) -> None:
        """在 anchor_rect（宠物精灵矩形）上方居中绘制气泡。"""
        if self._timer <= 0 or not self._text:
            return

        line_height = self.font.get_linesize()
        lines = wrap_text(self.font, self._text, MAX_WIDTH - 2 * PADDING)
        line_surfaces = [self.font.render(line, True, theme.TEXT_COLOR) for line in lines]

        content_width = max((s.get_width() for s in line_surfaces), default=0)
        width = min(content_width + 2 * PADDING, MAX_WIDTH)
        height = len(lines) * line_height + 2 * PADDING

        # 气泡主体置于宠物头顶上方，并整体限制在屏幕范围内
        screen_rect = surface.get_rect()
        x = anchor_rect.centerx - width // 2
        x = max(4, min(x, screen_rect.right - width - 4))
        y = anchor_rect.top - GAP - TAIL_HEIGHT - height
        y = max(4, y)

        bubble = theme.make_panel(
            (width, height), bg=theme.PET_BUBBLE_COLOR, border=theme.BORDER_COLOR
        )
        for index, text_surface in enumerate(line_surfaces):
            bubble.blit(text_surface, (PADDING, PADDING + index * line_height))
        surface.blit(bubble, (x, y))

        # 指向宠物的小尾巴（三角形），尽量对准宠物中心
        tip_x = max(x + TAIL_WIDTH, min(anchor_rect.centerx, x + width - TAIL_WIDTH))
        tail_top = y + height
        pygame.draw.polygon(
            surface,
            theme.PET_BUBBLE_COLOR,
            [
                (tip_x - TAIL_WIDTH // 2, tail_top - 1),
                (tip_x + TAIL_WIDTH // 2, tail_top - 1),
                (tip_x, tail_top + TAIL_HEIGHT),
            ],
        )
