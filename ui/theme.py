"""UI 共享主题模块。

集中管理聊天窗口 / 数值面板 / 设置窗口共用的配色常量，
避免各 UI 模块重复定义、风格漂移。
"""

from __future__ import annotations

import pygame

# ----- 圆角面板 -----
# 所有界面窗口/面板统一的圆角半径
PANEL_RADIUS = 14


def make_panel(
    size,
    *,
    radius: int = PANEL_RADIUS,
    bg=None,
    border=None,
    border_width: int = 1,
) -> pygame.Surface:
    """创建一个带圆角背景与边框的透明面板 Surface。

    返回 SRCALPHA 表面：圆角矩形以内为不透明背景，四角保持透明，
    blit 到透明色键窗口上即呈现圆角效果。各 UI 模块在其上继续 blit
    标题/控件即可，无需关心圆角裁剪。
    """
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rect = surface.get_rect()
    pygame.draw.rect(surface, bg or PANEL_BG_COLOR, rect, border_radius=radius)
    if border_width:
        pygame.draw.rect(surface, border or BORDER_COLOR, rect, border_width, border_radius=radius)
    return surface


# ----- 面板基础配色 -----
PANEL_BG_COLOR = (255, 255, 255)
BORDER_COLOR = (160, 160, 160)
TITLE_COLOR = (60, 60, 60)
TEXT_COLOR = (40, 40, 40)
LABEL_COLOR = (60, 60, 60)
PLACEHOLDER_COLOR = (150, 150, 150)

# ----- 输入框 -----
FIELD_BG_COLOR = (245, 245, 245)
FIELD_FOCUS_BORDER = (90, 140, 220)

# ----- 按钮 -----
BUTTON_BG_COLOR = (235, 242, 250)
BUTTON_BORDER_COLOR = (150, 170, 200)
BUTTON_TEXT_COLOR = (40, 60, 90)

# ----- 聊天气泡 -----
USER_BUBBLE_COLOR = (210, 235, 255)
PET_BUBBLE_COLOR = (255, 230, 240)

# ----- 状态提示 -----
STATUS_OK_COLOR = (60, 150, 70)
STATUS_FAIL_COLOR = (200, 70, 70)
STATUS_PENDING_COLOR = (120, 120, 120)
