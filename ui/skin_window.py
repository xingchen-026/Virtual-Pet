"""皮肤选择窗口模块。

SkinWindow 是从右键面板「皮肤」按钮打开的顶级弹窗，以缩略图预览的
方式展示可选皮肤（内置 default + assets/skins/ 下各皮肤），用户点击
某个预览即切换为该皮肤（即时生效，当前皮肤高亮标记）。

窗口右下角有「创建皮肤」按钮，其具体实现暂时搁置——点击后仅显示
占位提示，不执行实际创建逻辑。

SkinWindow 只负责渲染与事件解析：缩略图由 open() 传入的代表帧路径
即时加载缩放；选择结果通过 handle_event 返回给 UIManager，由其调用
皮肤切换回调。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from ui import theme

PADDING = 14
TITLE_HEIGHT = 26
THUMB_SIZE = 72
CELL_W = 88
CELL_H = 98
COLUMNS = 3

CREATE_BUTTON_SIZE = (92, 28)
SELECTED_BORDER = (90, 140, 220)
PLACEHOLDER_COLOR = (225, 225, 225)

TITLE_TEXT = "选择皮肤 (Esc 关闭)"
CREATE_TEXT = "创建皮肤"


class SkinWindow:
    """皮肤选择弹窗：缩略图预览选择 + 右下角创建皮肤按钮（功能搁置）。"""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect) -> None:
        self.font = font
        self.rect = rect
        self.visible = False
        self.active_skin = "default"
        self.status = ""

        # [(皮肤名, 缩略图 Surface 或 None)]
        self._items: List[Tuple[str, Optional[pygame.Surface]]] = []
        # [(命中矩形(窗口坐标), 皮肤名)]
        self._thumb_hit: List[Tuple[pygame.Rect, str]] = []
        self._create_hit: Optional[pygame.Rect] = None

    def open(self, items: List[Tuple[str, Optional[str]]], active_skin: str) -> None:
        """打开窗口。items 为 [(皮肤名, 代表帧路径或 None)]。"""
        self.visible = True
        self.active_skin = active_skin
        self.status = ""
        self._items = [(name, self._load_thumb(path)) for name, path in items]

    def close(self) -> None:
        self.visible = False

    def set_status(self, text: str) -> None:
        self.status = text

    def set_active(self, skin_name: str) -> None:
        self.active_skin = skin_name

    @staticmethod
    def _load_thumb(path: Optional[str]) -> Optional[pygame.Surface]:
        if not path:
            return None
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(image, (THUMB_SIZE, THUMB_SIZE))
        except Exception:
            return None

    def handle_event(self, event: pygame.event.Event) -> Optional[tuple]:
        """处理事件，返回 ("select", 皮肤名) / ("create", None) / ("close", None) / None。"""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visible = False
            return ("close", None)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._create_hit is not None and self._create_hit.collidepoint(event.pos):
                return ("create", None)
            for rect, name in self._thumb_hit:
                if rect.collidepoint(event.pos):
                    return ("select", name)

        return None

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        panel = pygame.Surface(self.rect.size)
        panel.fill(theme.PANEL_BG_COLOR)
        pygame.draw.rect(panel, theme.BORDER_COLOR, panel.get_rect(), 1)

        title = self.font.render(TITLE_TEXT, True, theme.TITLE_COLOR)
        panel.blit(title, (PADDING, PADDING))
        pygame.draw.line(
            panel, theme.BORDER_COLOR,
            (PADDING, TITLE_HEIGHT + 4), (self.rect.width - PADDING, TITLE_HEIGHT + 4),
        )

        self._thumb_hit = []
        grid_top = TITLE_HEIGHT + 12
        for index, (name, thumb) in enumerate(self._items):
            col = index % COLUMNS
            row = index // COLUMNS
            cell_x = PADDING + col * CELL_W
            cell_y = grid_top + row * CELL_H
            self._draw_cell(panel, cell_x, cell_y, name, thumb)

        self._draw_create_button(panel)

        if self.status:
            status = self.font.render(self.status, True, theme.STATUS_PENDING_COLOR)
            panel.blit(status, (PADDING, self.rect.height - PADDING - status.get_height()))

        surface.blit(panel, self.rect.topleft)

    def _draw_cell(self, panel, cell_x, cell_y, name, thumb) -> None:
        thumb_rect = pygame.Rect(cell_x, cell_y, THUMB_SIZE, THUMB_SIZE)

        if thumb is not None:
            panel.blit(thumb, thumb_rect)
        else:
            pygame.draw.rect(panel, PLACEHOLDER_COLOR, thumb_rect, border_radius=6)

        # 当前皮肤高亮边框
        is_active = name == self.active_skin
        border_color = SELECTED_BORDER if is_active else theme.BORDER_COLOR
        pygame.draw.rect(panel, border_color, thumb_rect, 3 if is_active else 1, border_radius=6)

        label = self.font.render(name, True, theme.TEXT_COLOR)
        label_x = cell_x + (THUMB_SIZE - label.get_width()) // 2
        panel.blit(label, (label_x, cell_y + THUMB_SIZE + 2))

        # 记录命中区域（窗口坐标 = 面板坐标 + 窗口左上角）
        self._thumb_hit.append((thumb_rect.move(self.rect.x, self.rect.y), name))

    def _draw_create_button(self, panel) -> None:
        width, height = CREATE_BUTTON_SIZE
        rect = pygame.Rect(
            self.rect.width - PADDING - width,
            self.rect.height - PADDING - height,
            width, height,
        )
        pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=6)
        pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=6)
        text = self.font.render(CREATE_TEXT, True, theme.BUTTON_TEXT_COLOR)
        panel.blit(text, text.get_rect(center=rect.center))

        self._create_hit = rect.move(self.rect.x, self.rect.y)
