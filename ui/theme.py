"""UI 共享主题模块。

集中管理聊天窗口 / 数值面板 / 设置窗口共用的配色常量，
避免各 UI 模块重复定义、风格漂移。
"""

from __future__ import annotations

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
