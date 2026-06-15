"""设置窗口模块。

SettingsWindow 提供一个模态设置面板（从右键面板的"设置"按钮打开）：

* 宠物大小：[-] / [+] 按钮调节缩放倍数（范围/步长见 settings）
* AI 服务配置：服务商（点击切换）、模型名称、API Key（输入框，
  Key 显示为掩码）

窗口打开期间吞掉全部输入事件（模态），Esc 或"关闭"按钮退出，
"保存"按钮收集当前编辑值返回给 Game 应用并持久化；
本模块只负责 UI，不直接读写配置文件或修改游戏对象。
"""

from __future__ import annotations

from typing import Dict, Optional

import pygame

from config import settings
from ui import theme

TITLE_TEXT = "设置"

PADDING = 12
ROW_HEIGHT = 34
FIELD_HEIGHT = 26
BUTTON_HEIGHT = 28
MAX_FIELD_LENGTH = 120

# 可选的 LLM 服务商（点击循环切换）
PROVIDERS = ["deepseek", "openai", "local"]


class SettingsWindow:
    """模态设置窗口：宠物大小 + AI 服务配置。"""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect) -> None:
        self.font = font
        self.rect = rect
        self.visible = False

        self.name = ""
        self.character = ""
        self.tone = ""
        self.pet_scale = settings.PET_SCALE_DEFAULT
        self.reminder_interval = settings.REST_REMINDER_INTERVAL_MINUTES
        self.proactive_enabled = settings.PROACTIVE_CHAT_ENABLED
        self.proactive_interval = settings.PROACTIVE_CHAT_INTERVAL_MINUTES
        self.provider = PROVIDERS[0]
        self.base_url = ""
        self.model = ""
        self.api_key = ""

        # 服务商下拉是否展开
        self._provider_open = False

        # 连接测试状态行：(文本, 是否成功/None=进行中)
        self.status: str = ""
        self.status_ok = None

        # 当前聚焦的文本输入字段（含 base_url）
        self._focus: Optional[str] = None
        # 控件名 -> 窗口坐标命中区域（draw 时刷新）
        self._hit_areas: Dict[str, pygame.Rect] = {}

    def open(
        self, pet_scale: float, name: str, character: str, tone: str, ai_config: dict,
        reminder_interval: float = settings.REST_REMINDER_INTERVAL_MINUTES,
        proactive_enabled: bool = settings.PROACTIVE_CHAT_ENABLED,
        proactive_interval: float = settings.PROACTIVE_CHAT_INTERVAL_MINUTES,
    ) -> None:
        """打开设置窗口，并以当前配置初始化各编辑项。"""
        self.visible = True
        self.name = name
        self.character = character
        self.tone = tone
        self.pet_scale = pet_scale
        self.reminder_interval = reminder_interval
        self.proactive_enabled = proactive_enabled
        self.proactive_interval = proactive_interval
        self.provider = ai_config.get("provider", PROVIDERS[0])
        if self.provider not in PROVIDERS:
            PROVIDERS.append(self.provider)
        self.base_url = ai_config.get("api_base", "")
        self.model = ai_config.get("model", "")
        self.api_key = ai_config.get("api_key", "")
        self._provider_open = False
        self.status = ""
        self.status_ok = None
        self._focus = None
        pygame.key.start_text_input()

    def set_status(self, text: str, ok) -> None:
        """更新连接测试状态行（ok: True 成功 / False 失败 / None 进行中）。"""
        self.status = text
        self.status_ok = ok

    def handle_event(self, event: pygame.event.Event) -> Optional[dict]:
        """处理输入事件（模态期间所有事件均应路由到此）。

        返回值：
        * {"action": "save", "pet_scale": ..., "ai_config": {...}} —— 点击保存
        * {"action": "close"} —— Esc / 点击关闭
        * None —— 事件已消化，无需上层处理
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return self._close()
            if event.key == pygame.K_BACKSPACE and self._focus:
                value = getattr(self, self._focus)
                setattr(self, self._focus, value[:-1])
            if (
                event.key == pygame.K_v
                and event.mod & pygame.KMOD_CTRL
                and self._focus
            ):
                self._paste_into_focus()
            return None

        if event.type == pygame.TEXTINPUT and self._focus:
            value = getattr(self, self._focus)
            if len(value) < MAX_FIELD_LENGTH:
                setattr(self, self._focus, value + event.text)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)

        return None

    def _handle_click(self, pos) -> Optional[dict]:
        # 下拉展开时，优先处理选项点击（选项浮层覆盖在其它控件之上）
        if self._provider_open:
            for name, rect in self._hit_areas.items():
                if name.startswith("opt:") and rect.collidepoint(pos):
                    self.provider = name.split(":", 1)[1]
                    self._provider_open = False
                    return None
            self._provider_open = False  # 点别处收起下拉
            # 不 return，继续判断本次点击是否落在其它控件上

        for name, rect in self._hit_areas.items():
            if name.startswith("opt:") or not rect.collidepoint(pos):
                continue

            if name == "scale_minus":
                self.pet_scale = max(
                    settings.PET_SCALE_MIN, round(self.pet_scale - settings.PET_SCALE_STEP, 2)
                )
            elif name == "scale_plus":
                self.pet_scale = min(
                    settings.PET_SCALE_MAX, round(self.pet_scale + settings.PET_SCALE_STEP, 2)
                )
            elif name == "reminder_minus":
                self.reminder_interval = max(
                    settings.REMINDER_INTERVAL_MIN,
                    self.reminder_interval - settings.REMINDER_INTERVAL_STEP,
                )
            elif name == "reminder_plus":
                self.reminder_interval = min(
                    settings.REMINDER_INTERVAL_MAX,
                    self.reminder_interval + settings.REMINDER_INTERVAL_STEP,
                )
            elif name == "proactive_toggle":
                self.proactive_enabled = not self.proactive_enabled
            elif name == "proactive_minus":
                self.proactive_interval = max(
                    settings.PROACTIVE_INTERVAL_MIN,
                    self.proactive_interval - settings.PROACTIVE_INTERVAL_STEP,
                )
            elif name == "proactive_plus":
                self.proactive_interval = min(
                    settings.PROACTIVE_INTERVAL_MAX,
                    self.proactive_interval + settings.PROACTIVE_INTERVAL_STEP,
                )
            elif name == "provider":
                self._provider_open = not self._provider_open
            elif name in ("name", "character", "tone", "base_url", "model", "api_key"):
                self._focus = name
                # 将输入法候选窗口定位到输入框处
                pygame.key.set_text_input_rect(rect)
            elif name == "save":
                return self._save()
            elif name == "save_exit":
                return self._save_exit()
            elif name == "test":
                return {"action": "test", "ai_config": self._collect_ai_config()}
            elif name == "close":
                return self._close()
            return None

        self._focus = None
        return None

    def _paste_into_focus(self) -> None:
        """将系统剪贴板文本粘贴到当前聚焦的输入框（Ctrl+V）。

        API Key 等长字符串逐字输入不便（且可能被输入法拦截），
        粘贴是主要录入方式。
        """
        text = self._read_clipboard().strip().replace("\r", "").replace("\n", "")
        if not text:
            return

        value = getattr(self, self._focus)
        combined = (value + text)[:MAX_FIELD_LENGTH]
        setattr(self, self._focus, combined)

    @staticmethod
    def _read_clipboard() -> str:
        """读取系统剪贴板文本，优先 pygame.scrap，失败时回退 win32clipboard。"""
        try:
            text = pygame.scrap.get_text()
            if text:
                return text
        except Exception:
            pass

        try:
            import win32clipboard

            win32clipboard.OpenClipboard()
            try:
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return ""

    def _collect_ai_config(self) -> dict:
        return {
            "provider": self.provider,
            "api_base": self.base_url.strip(),
            "model": self.model.strip(),
            "api_key": self.api_key.strip(),
        }

    def _save(self) -> dict:
        self.visible = False
        return self._result("save")

    def _save_exit(self) -> dict:
        """保存当前编辑值并请求退出（字段同 _save，仅 action 不同）。"""
        self.visible = False
        return self._result("save_exit")

    def _result(self, action: str) -> dict:
        return {
            "action": action,
            "name": self.name.strip(),
            "character": self.character.strip(),
            "tone": self.tone.strip(),
            "pet_scale": self.pet_scale,
            "reminder_interval": self.reminder_interval,
            "proactive_enabled": self.proactive_enabled,
            "proactive_interval": self.proactive_interval,
            "ai_config": self._collect_ai_config(),
        }

    def _close(self) -> dict:
        self.visible = False
        return {"action": "close"}

    def draw(self, surface: pygame.Surface) -> None:
        """绘制设置窗口，并刷新各控件的命中区域。"""
        if not self.visible:
            return

        panel = theme.make_panel(self.rect.size)

        self._hit_areas = {}
        line_height = self.font.get_linesize()

        title = self.font.render(f"{TITLE_TEXT} (Esc 关闭)", True, theme.LABEL_COLOR)
        panel.blit(title, (PADDING, PADDING))
        pygame.draw.line(
            panel, theme.BORDER_COLOR,
            (PADDING, PADDING + line_height + 2),
            (self.rect.width - PADDING, PADDING + line_height + 2),
        )

        y = PADDING + line_height + 10
        y = self._draw_field_row(panel, y, "名称", "name", self.name)
        y = self._draw_field_row(panel, y, "性格", "character", self.character)
        y = self._draw_field_row(panel, y, "语气", "tone", self.tone)
        y = self._draw_scale_row(panel, y)
        y = self._draw_reminder_row(panel, y)
        y = self._draw_toggle_row(
            panel, y, "主动互动", self.proactive_enabled, "proactive_toggle"
        )
        y = self._draw_stepper_row(
            panel, y, "互动间隔", f"{self.proactive_interval:g}分",
            "proactive_minus", "proactive_plus",
        )
        provider_rect, y = self._draw_provider_row(panel, y)
        y = self._draw_field_row(panel, y, "接口地址", "base_url", self.base_url or "（默认）")
        y = self._draw_field_row(panel, y, "模型", "model", self.model)
        y = self._draw_field_row(panel, y, "API Key", "api_key", self._masked_key())
        self._draw_status_row(panel, y)
        self._draw_bottom_buttons(panel)

        # 下拉浮层最后绘制，覆盖在其它行之上
        if self._provider_open:
            self._draw_provider_popup(panel, provider_rect)

        surface.blit(panel, self.rect.topleft)

        # 命中区域转换为窗口坐标
        self._hit_areas = {
            name: rect.move(self.rect.x, self.rect.y)
            for name, rect in self._hit_areas.items()
        }

    def _draw_scale_row(self, panel: pygame.Surface, y: int) -> int:
        label = self.font.render("宠物大小", True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))

        value_x = self.rect.width // 2
        minus_rect = pygame.Rect(value_x, y, FIELD_HEIGHT, FIELD_HEIGHT)
        value_rect = pygame.Rect(minus_rect.right + 6, y, 56, FIELD_HEIGHT)
        plus_rect = pygame.Rect(value_rect.right + 6, y, FIELD_HEIGHT, FIELD_HEIGHT)

        for name, rect, text in (
            ("scale_minus", minus_rect, "-"),
            ("scale_plus", plus_rect, "+"),
        ):
            pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=4)
            pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=4)
            glyph = self.font.render(text, True, theme.BUTTON_TEXT_COLOR)
            panel.blit(glyph, glyph.get_rect(center=rect.center))
            self._hit_areas[name] = rect

        value = self.font.render(f"{self.pet_scale:.1f}x", True, theme.TEXT_COLOR)
        panel.blit(value, value.get_rect(center=value_rect.center))

        return y + ROW_HEIGHT

    def _draw_reminder_row(self, panel: pygame.Surface, y: int) -> int:
        """休息提醒间隔（分钟）：[-] / [+] 按钮调节。"""
        label = self.font.render("提醒间隔", True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))

        value_x = self.rect.width // 2
        minus_rect = pygame.Rect(value_x, y, FIELD_HEIGHT, FIELD_HEIGHT)
        value_rect = pygame.Rect(minus_rect.right + 6, y, 56, FIELD_HEIGHT)
        plus_rect = pygame.Rect(value_rect.right + 6, y, FIELD_HEIGHT, FIELD_HEIGHT)

        for name, rect, text in (
            ("reminder_minus", minus_rect, "-"),
            ("reminder_plus", plus_rect, "+"),
        ):
            pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=4)
            pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=4)
            glyph = self.font.render(text, True, theme.BUTTON_TEXT_COLOR)
            panel.blit(glyph, glyph.get_rect(center=rect.center))
            self._hit_areas[name] = rect

        value = self.font.render(f"{self.reminder_interval:g}分", True, theme.TEXT_COLOR)
        panel.blit(value, value.get_rect(center=value_rect.center))

        return y + ROW_HEIGHT

    def _draw_stepper_row(
        self, panel: pygame.Surface, y: int, label_text: str, value_text: str,
        minus_name: str, plus_name: str,
    ) -> int:
        """通用「标签 + [-] 数值 [+]」步进行（与提醒/大小行同款布局）。"""
        label = self.font.render(label_text, True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))

        value_x = self.rect.width // 2
        minus_rect = pygame.Rect(value_x, y, FIELD_HEIGHT, FIELD_HEIGHT)
        value_rect = pygame.Rect(minus_rect.right + 6, y, 56, FIELD_HEIGHT)
        plus_rect = pygame.Rect(value_rect.right + 6, y, FIELD_HEIGHT, FIELD_HEIGHT)

        for name, rect, text in (
            (minus_name, minus_rect, "-"),
            (plus_name, plus_rect, "+"),
        ):
            pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=4)
            pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=4)
            glyph = self.font.render(text, True, theme.BUTTON_TEXT_COLOR)
            panel.blit(glyph, glyph.get_rect(center=rect.center))
            self._hit_areas[name] = rect

        value = self.font.render(value_text, True, theme.TEXT_COLOR)
        panel.blit(value, value.get_rect(center=value_rect.center))
        return y + ROW_HEIGHT

    def _draw_toggle_row(
        self, panel: pygame.Surface, y: int, label_text: str, on: bool, toggle_name: str,
    ) -> int:
        """通用「标签 + [开/关] 切换」行；开为高亮、关为灰底。"""
        label = self.font.render(label_text, True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))

        rect = pygame.Rect(self.rect.width // 2, y, 56, FIELD_HEIGHT)
        bg = theme.ACCENT_COLOR if on else theme.BUTTON_BG_COLOR
        pygame.draw.rect(panel, bg, rect, border_radius=4)
        pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=4)
        text = self.font.render("开" if on else "关", True, theme.BUTTON_TEXT_COLOR)
        panel.blit(text, text.get_rect(center=rect.center))
        self._hit_areas[toggle_name] = rect
        return y + ROW_HEIGHT

    def _draw_provider_row(self, panel: pygame.Surface, y: int):
        """绘制服务商下拉框（点击展开选项），返回 (字段矩形, 下一个 y)。"""
        label = self.font.render("服务商", True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))

        rect = pygame.Rect(self.rect.width // 2, y, self.rect.width // 2 - PADDING, FIELD_HEIGHT)
        pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=4)
        pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=4)
        text = self.font.render(self.provider, True, theme.BUTTON_TEXT_COLOR)
        panel.blit(text, text.get_rect(midleft=(rect.x + 6, rect.centery)))
        arrow = self.font.render("▾", True, theme.BUTTON_TEXT_COLOR)
        panel.blit(arrow, arrow.get_rect(midright=(rect.right - 6, rect.centery)))
        self._hit_areas["provider"] = rect
        return rect, y + ROW_HEIGHT

    def _draw_provider_popup(self, panel: pygame.Surface, field_rect: pygame.Rect) -> None:
        """在服务商字段下方绘制下拉选项浮层，并登记各选项命中区。"""
        for i, provider in enumerate(PROVIDERS):
            opt = pygame.Rect(field_rect.x, field_rect.bottom + i * FIELD_HEIGHT,
                              field_rect.width, FIELD_HEIGHT)
            active = provider == self.provider
            pygame.draw.rect(panel, theme.FIELD_FOCUS_BORDER if active else theme.PANEL_BG_COLOR, opt)
            pygame.draw.rect(panel, theme.BORDER_COLOR, opt, 1)
            color = (255, 255, 255) if active else theme.TEXT_COLOR
            text = self.font.render(provider, True, color)
            panel.blit(text, text.get_rect(midleft=(opt.x + 6, opt.centery)))
            self._hit_areas[f"opt:{provider}"] = opt

    def _draw_field_row(
        self, panel: pygame.Surface, y: int, label_text: str, name: str, display: str
    ) -> int:
        label = self.font.render(label_text, True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))

        rect = pygame.Rect(
            self.rect.width // 2, y, self.rect.width // 2 - PADDING, FIELD_HEIGHT
        )
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, rect, border_radius=4)
        border = theme.FIELD_FOCUS_BORDER if self._focus == name else theme.BORDER_COLOR
        pygame.draw.rect(panel, border, rect, 1, border_radius=4)

        text = self.font.render(display, True, theme.TEXT_COLOR)
        clip = panel.get_clip()
        panel.set_clip(rect.inflate(-8, 0))
        panel.blit(text, (rect.x + 6, rect.y + (rect.height - text.get_height()) // 2))
        panel.set_clip(clip)

        self._hit_areas[name] = rect
        return y + ROW_HEIGHT

    def _masked_key(self) -> str:
        """API Key 显示首尾明文、中间掩码，便于确认粘贴的内容是否正确。"""
        key = self.api_key
        if not key:
            return ""
        if len(key) <= 10:
            return "*" * len(key)
        return f"{key[:6]}...{key[-4:]}"

    def _draw_status_row(self, panel: pygame.Surface, y: int) -> None:
        """绘制连接测试状态（成功绿色 / 失败红色 / 进行中灰色），自动换行。"""
        if not self.status:
            return

        if self.status_ok is True:
            color = theme.STATUS_OK_COLOR
        elif self.status_ok is False:
            color = theme.STATUS_FAIL_COLOR
        else:
            color = theme.STATUS_PENDING_COLOR

        from ui.message_box import wrap_text

        max_width = self.rect.width - 2 * PADDING
        max_lines = max(
            1,
            (self.rect.height - BUTTON_HEIGHT - 2 * PADDING - y) // self.font.get_linesize(),
        )
        for index, line in enumerate(wrap_text(self.font, self.status, max_width)[:max_lines]):
            text = self.font.render(line, True, color)
            panel.blit(text, (PADDING, y + 4 + index * self.font.get_linesize()))

    def _draw_bottom_buttons(self, panel: pygame.Surface) -> None:
        # 底行：保存 / 测试 / 关闭
        buttons = (("save", "保存"), ("test", "测试"), ("close", "关闭"))
        button_width = (self.rect.width - (len(buttons) + 1) * PADDING) // len(buttons)
        y = self.rect.height - BUTTON_HEIGHT - PADDING

        for index, (name, text) in enumerate(buttons):
            rect = pygame.Rect(
                PADDING + index * (button_width + PADDING), y, button_width, BUTTON_HEIGHT
            )
            pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=6)
            pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=6)
            glyph = self.font.render(text, True, theme.BUTTON_TEXT_COLOR)
            panel.blit(glyph, glyph.get_rect(center=rect.center))
            self._hit_areas[name] = rect

        # 底行上方：整宽「保存并退出」按钮（保存数据后关闭进程）
        exit_rect = pygame.Rect(
            PADDING, y - BUTTON_HEIGHT - PADDING,
            self.rect.width - 2 * PADDING, BUTTON_HEIGHT,
        )
        pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, exit_rect, border_radius=6)
        pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, exit_rect, 1, border_radius=6)
        exit_glyph = self.font.render("保存并退出", True, theme.BUTTON_TEXT_COLOR)
        panel.blit(exit_glyph, exit_glyph.get_rect(center=exit_rect.center))
        self._hit_areas["save_exit"] = exit_rect
