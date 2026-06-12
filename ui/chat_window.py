"""AI 对话窗口模块。

ChatWindow 提供一个可在主窗口内显示/隐藏的聊天面板：

* 输入框：接收键盘文本输入（TEXTINPUT），按 Enter 提交
* 消息历史：用户与宠物的对话气泡，支持鼠标滚轮滚动
* 状态提示：AI 正在等待回复时显示"对方正在输入"提示

ChatWindow 只负责 UI 渲染与输入事件解析，不直接调用
core.ai.ai_service.AIService；core.game.Game 在收到
handle_event() 返回的用户消息后，自行调用 AIService 并将结果通过
add_message() 回填，从而保持 UI 与 AI 服务解耦。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from ui.message_box import MessageBox

PANEL_BG_COLOR = (255, 255, 255)
BORDER_COLOR = (180, 180, 180)
INPUT_BG_COLOR = (245, 245, 245)
PLACEHOLDER_COLOR = (150, 150, 150)
TEXT_COLOR = (40, 40, 40)
TITLE_COLOR = (80, 80, 80)

PADDING = 8
TITLE_HEIGHT = 22
INPUT_HEIGHT = 28
SCROLL_STEP = 24
MAX_INPUT_LENGTH = 200


class ChatWindow:
    """宠物 AI 对话窗口：标题栏 + 消息历史 + 输入框。"""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect, pet_name: str = "Pet") -> None:
        self.font = font
        self.rect = rect
        self.pet_name = pet_name

        self.visible = False
        self.pending = False
        self.input_text = ""
        self.scroll_offset = 0

        self._boxes: List[MessageBox] = []

    def toggle(self) -> None:
        """切换对话窗口的显示/隐藏，并同步开启/关闭文本输入。"""
        self.visible = not self.visible
        if self.visible:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()

    def add_message(self, sender: str, text: str) -> None:
        """追加一条消息（sender 为 "user" 或 "pet"）到历史记录末尾。"""
        max_width = self.rect.width - 2 * PADDING
        self._boxes.append(MessageBox(self.font, sender, text, max_width))
        self.scroll_offset = 0

    def set_pending(self, pending: bool) -> None:
        """设置是否处于"等待 AI 回复"状态，输入框会显示对应提示文案。"""
        self.pending = pending

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """处理对话窗口的输入事件。

        返回用户按下 Enter 提交的消息文本；其余情况返回 None。
        仅在 self.visible 为真时处理事件。
        """
        if not self.visible:
            return None

        if event.type == pygame.TEXTINPUT:
            if len(self.input_text) < MAX_INPUT_LENGTH:
                self.input_text += event.text
            return None

        if event.type == pygame.KEYDOWN:
            return self._handle_key_down(event.key)

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, self.scroll_offset - event.y * SCROLL_STEP)
            return None

        return None

    def _handle_key_down(self, key: int) -> Optional[str]:
        if key == pygame.K_ESCAPE:
            self.toggle()
            return None

        if key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
            return None

        if key == pygame.K_RETURN:
            if self.pending:
                return None

            message = self.input_text.strip()
            if not message:
                return None

            self.input_text = ""
            return message

        return None

    def draw(self, surface: pygame.Surface) -> None:
        """绘制对话窗口面板（标题栏 / 消息历史 / 输入框）。"""
        if not self.visible:
            return

        panel = pygame.Surface(self.rect.size)
        panel.fill(PANEL_BG_COLOR)
        pygame.draw.rect(panel, BORDER_COLOR, panel.get_rect(), 1)

        title_surface = self.font.render(f"和 {self.pet_name} 聊天 (Esc 关闭)", True, TITLE_COLOR)
        panel.blit(title_surface, (PADDING, (TITLE_HEIGHT - title_surface.get_height()) // 2))
        pygame.draw.line(
            panel, BORDER_COLOR,
            (0, TITLE_HEIGHT), (self.rect.width, TITLE_HEIGHT),
        )

        history_rect = pygame.Rect(
            PADDING, TITLE_HEIGHT + PADDING,
            self.rect.width - 2 * PADDING,
            self.rect.height - TITLE_HEIGHT - INPUT_HEIGHT - 3 * PADDING,
        )
        self._draw_history(panel, history_rect)

        input_rect = pygame.Rect(
            PADDING, self.rect.height - INPUT_HEIGHT - PADDING,
            self.rect.width - 2 * PADDING, INPUT_HEIGHT,
        )
        self._draw_input(panel, input_rect)

        surface.blit(panel, self.rect.topleft)

    def _draw_history(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        self._clamp_scroll(area.height)

        clip = surface.get_clip()
        surface.set_clip(area)

        y = area.bottom - self.scroll_offset
        for box in reversed(self._boxes):
            y -= box.height
            if y + box.height >= area.top:
                box.draw(surface, area.x, y)
            if y < area.top - box.height:
                break

        surface.set_clip(clip)

    def _draw_input(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, INPUT_BG_COLOR, rect, border_radius=4)
        pygame.draw.rect(surface, BORDER_COLOR, rect, 1, border_radius=4)

        if self.input_text:
            display_text, color = self.input_text, TEXT_COLOR
        elif self.pending:
            display_text, color = f"{self.pet_name} 正在输入...", PLACEHOLDER_COLOR
        else:
            display_text, color = "输入消息，按 Enter 发送", PLACEHOLDER_COLOR

        text_surface = self.font.render(display_text, True, color)
        surface.blit(
            text_surface,
            (rect.x + 6, rect.y + (rect.height - text_surface.get_height()) // 2),
        )

    def _content_height(self) -> int:
        return sum(box.height for box in self._boxes)

    def _clamp_scroll(self, area_height: int) -> None:
        max_offset = max(0, self._content_height() - area_height)
        self.scroll_offset = max(0, min(self.scroll_offset, max_offset))
