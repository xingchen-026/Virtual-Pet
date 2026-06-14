"""食物图标绘制模块。

draw_food 用 pygame.draw 程序化绘制一个小苹果（红身 + 棕柄 + 绿叶 + 高光），
供放置模式下跟随鼠标、以及已放下的食物在桌面上的渲染，无需额外美术资源。
绘制位置由调用方给出（窗口画布坐标系下的中心点）。
"""

from __future__ import annotations

from typing import Tuple

import pygame

from config import settings

_BODY_COLOR = (220, 60, 60)
_STEM_COLOR = (110, 70, 40)
_LEAF_COLOR = (90, 170, 80)
_HIGHLIGHT_COLOR = (255, 200, 200)


def draw_food(surface: pygame.Surface, center: Tuple[int, int]) -> None:
    """在 surface 的 center 处绘制一个小苹果。"""
    cx, cy = int(center[0]), int(center[1])
    radius = settings.FOOD_ICON_RADIUS

    # 柄与叶（在果身上方）
    pygame.draw.line(surface, _STEM_COLOR, (cx, cy - radius), (cx, cy - radius - 5), 2)
    leaf = pygame.Rect(0, 0, radius, radius // 2)
    leaf.center = (cx + radius // 2, cy - radius - 2)
    pygame.draw.ellipse(surface, _LEAF_COLOR, leaf)

    # 果身
    pygame.draw.circle(surface, _BODY_COLOR, (cx, cy), radius)
    # 高光
    pygame.draw.circle(surface, _HIGHLIGHT_COLOR, (cx - radius // 3, cy - radius // 3), max(2, radius // 5))
