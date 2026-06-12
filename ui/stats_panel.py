"""宠物数值信息面板模块。

StatsPanel 提供一个右键点击宠物后弹出的信息面板，
显示宠物名称、状态、各属性数值、行为与 AI 服务状态等信息，
再次右键点击宠物（或点击面板外区域）即关闭。

面板内容由 Game 每帧传入（draw 的 lines 参数），
本模块只负责定位与渲染，不依赖 Pet / AIService 等业务对象。
"""

from __future__ import annotations

from typing import List, Tuple

import pygame

from config import settings

PANEL_BG_COLOR = (255, 255, 255)
BORDER_COLOR = (160, 160, 160)
TITLE_COLOR = (60, 60, 60)
TEXT_COLOR = (40, 40, 40)

TITLE_TEXT = "宠物状态"


class StatsPanel:
    """右键弹出的宠物数值信息面板。"""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.visible = False

    def toggle(self) -> None:
        """切换面板的显示/隐藏。"""
        self.visible = not self.visible

    def hide(self) -> None:
        """关闭面板。"""
        self.visible = False

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
        height = (len(lines) + 1) * line_height + 2 * padding

        x, y = self._panel_position(surface, anchor_rect, width, height)

        panel = pygame.Surface((width, height))
        panel.fill(PANEL_BG_COLOR)
        pygame.draw.rect(panel, BORDER_COLOR, panel.get_rect(), 1)

        title_surface = self.font.render(TITLE_TEXT, True, TITLE_COLOR)
        panel.blit(title_surface, (padding, padding))
        pygame.draw.line(
            panel, BORDER_COLOR,
            (padding, padding + line_height - 2),
            (width - padding, padding + line_height - 2),
        )

        text_y = padding + line_height
        for line in lines:
            text_surface = self.font.render(line, True, TEXT_COLOR)
            panel.blit(text_surface, (padding, text_y))
            text_y += line_height

        surface.blit(panel, (x, y))

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

        y = anchor_rect.top
        y = max(0, min(y, screen_rect.bottom - height))

        return x, y
