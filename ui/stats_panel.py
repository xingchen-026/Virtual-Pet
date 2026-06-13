"""宠物数值信息与功能面板模块。

StatsPanel 提供一个右键点击宠物后弹出的面板：

* 数值信息：宠物名称、状态、各属性数值、行为与 AI 服务状态等
* 功能按钮：喂食 / 玩耍 / 聊天（替代原先的键盘功能按键）

再次右键点击宠物即关闭。面板内容由 Game 每帧传入（draw 的
lines 参数），按钮点击通过 handle_click() 返回动作标识，
由 Game 分发为交互事件；本模块只负责定位、渲染与点击命中检测，
不依赖 Pet / AIService 等业务对象。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from config import settings
from ui import theme

TITLE_TEXT = "宠物状态"

# 功能按钮：按行排列的 (显示文字, 动作标识)，动作由 Game 分发
BUTTON_ROWS = [
    [("喂食", "feed"), ("玩耍", "play")],
    [("聊天", "chat"), ("设置", "settings")],
]

BUTTON_HEIGHT = 28
BUTTON_GAP = 8


class StatsPanel:
    """右键弹出的宠物数值信息与功能按钮面板。"""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.visible = False

        # 最近一次绘制的面板/按钮区域（窗口坐标），用于点击命中检测
        self._panel_rect: Optional[pygame.Rect] = None
        self._button_rects: List[Tuple[pygame.Rect, str]] = []

    def toggle(self) -> None:
        """切换面板的显示/隐藏。"""
        self.visible = not self.visible
        if not self.visible:
            self._clear_hit_areas()

    def hide(self) -> None:
        """关闭面板。"""
        self.visible = False
        self._clear_hit_areas()

    def contains(self, position: Tuple[int, int]) -> bool:
        """判断窗口坐标是否落在面板范围内（面板不可见时恒为 False）。"""
        return (
            self.visible
            and self._panel_rect is not None
            and self._panel_rect.collidepoint(position)
        )

    def handle_click(self, position: Tuple[int, int]) -> Optional[str]:
        """处理面板内的左键点击，命中按钮时返回其动作标识。"""
        for rect, action in self._button_rects:
            if rect.collidepoint(position):
                return action
        return None

    def draw(
        self,
        surface: pygame.Surface,
        anchor_rect: pygame.Rect,
        lines: List[str],
    ) -> None:
        """在宠物旁边绘制面板。

        anchor_rect: 宠物精灵的矩形，面板优先显示在其右侧，
        放不下时翻到左侧，并整体限制在窗口范围内。
        """
        if not self.visible or not lines:
            return

        padding = settings.STATS_PANEL_PADDING
        line_height = self.font.get_linesize()
        width = settings.STATS_PANEL_WIDTH
        buttons_height = len(BUTTON_ROWS) * (BUTTON_HEIGHT + BUTTON_GAP) - BUTTON_GAP
        height = (len(lines) + 1) * line_height + buttons_height + 3 * padding

        x, y = self._panel_position(surface, anchor_rect, width, height)
        self._panel_rect = pygame.Rect(x, y, width, height)

        panel = pygame.Surface((width, height))
        panel.fill(theme.PANEL_BG_COLOR)
        pygame.draw.rect(panel, theme.BORDER_COLOR, panel.get_rect(), 1)

        title_surface = self.font.render(TITLE_TEXT, True, theme.TITLE_COLOR)
        panel.blit(title_surface, (padding, padding))
        pygame.draw.line(
            panel, theme.BORDER_COLOR,
            (padding, padding + line_height - 2),
            (width - padding, padding + line_height - 2),
        )

        text_y = padding + line_height
        for line in lines:
            text_surface = self.font.render(line, True, theme.TEXT_COLOR)
            panel.blit(text_surface, (padding, text_y))
            text_y += line_height

        self._draw_buttons(panel, x, y, padding, text_y + padding)

        surface.blit(panel, (x, y))

    def _draw_buttons(
        self,
        panel: pygame.Surface,
        panel_x: int,
        panel_y: int,
        padding: int,
        buttons_y: int,
    ) -> None:
        """绘制底部功能按钮（多行排列），并记录各按钮的窗口坐标命中区域。"""
        width = panel.get_width()

        self._button_rects = []
        for row_index, row in enumerate(BUTTON_ROWS):
            count = len(row)
            button_width = (width - 2 * padding - (count - 1) * BUTTON_GAP) // count
            row_y = buttons_y + row_index * (BUTTON_HEIGHT + BUTTON_GAP)

            for index, (label, action) in enumerate(row):
                local_rect = pygame.Rect(
                    padding + index * (button_width + BUTTON_GAP),
                    row_y,
                    button_width,
                    BUTTON_HEIGHT,
                )
                pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, local_rect, border_radius=6)
                pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, local_rect, 1, border_radius=6)

                text_surface = self.font.render(label, True, theme.BUTTON_TEXT_COLOR)
                panel.blit(
                    text_surface,
                    (
                        local_rect.centerx - text_surface.get_width() // 2,
                        local_rect.centery - text_surface.get_height() // 2,
                    ),
                )

                self._button_rects.append(
                    (local_rect.move(panel_x, panel_y), action)
                )

    def _panel_position(
        self,
        surface: pygame.Surface,
        anchor_rect: pygame.Rect,
        width: int,
        height: int,
    ) -> Tuple[int, int]:
        """计算面板左上角坐标：优先宠物右侧，越界时翻转/收紧到窗口内。"""
        margin = settings.STATS_PANEL_MARGIN
        screen_rect = surface.get_rect()

        x = anchor_rect.right + margin
        if x + width > screen_rect.right:
            x = anchor_rect.left - margin - width
        x = max(0, min(x, screen_rect.right - width))

        # 垂直方向与宠物中心对齐，超出窗口时收紧
        y = anchor_rect.centery - height // 2
        y = max(0, min(y, screen_rect.bottom - height))

        return x, y

    def _clear_hit_areas(self) -> None:
        self._panel_rect = None
        self._button_rects = []
